#!/usr/bin/env python3
"""novelty_probe.http 的离线测试：用假传输层（按 URL 排队的响应）与可控的时钟、随机数；不联网。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import ROOT  # noqa: E402,F401

from novelty_probe import cache, http, schemas  # noqa: E402


class FakeTransport:
    """url → 响应队列；每次请求弹出一个。队列用完则重复最后一个。"""

    def __init__(self):
        self.queues, self.calls = {}, []

    def add(self, url, status, body=b"", headers=None, final_url=None):
        if isinstance(body, (dict, list)):
            body, headers = json.dumps(body).encode(), {"content-type": "application/json", **(headers or {})}
        elif isinstance(body, str):
            body = body.encode()
        self.queues.setdefault(url, []).append((status, {k.lower(): v for k, v in (headers or {}).items()}, body, final_url or url))

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body))
        q = self.queues.get(url)
        if not q:
            raise AssertionError(f"unexpected request {url}")
        item = q.pop(0) if len(q) > 1 else q[0]
        if isinstance(item[0], Exception):
            raise item[0]
        return item


class Clock:
    def __init__(self):
        self.t, self.sleeps = 1000.0, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(round(s, 3))
        self.t += s


class MaxRandom:
    def random(self):
        return 1.0


def make_client(ft, clock, mode="live", tmp=None, **kw):
    env = {"NP_HTTP_CACHE": str(Path(tmp or tempfile.mkdtemp()) / "cache")}
    env.update(kw.pop("env", {}))
    return http.Client(mode, env=env, clock=clock.now, sleep=clock.sleep, rng=MaxRandom(), transport=ft, **kw)


class TestRetryPolicy(unittest.TestCase):
    def test_retry_schedule_and_success(self):
        ft, clock = FakeTransport(), Clock()
        url = "https://example.test/flaky"
        ft.add(url, 429, {"message": "busy"})
        ft.add(url, 429, {"message": "busy"})
        ft.add(url, 200, {"ok": True})
        c = make_client(ft, clock)
        self.assertEqual(c.get_json(url), {"ok": True})
        self.assertEqual(clock.sleeps, [2, 4])                               # base 1 s × 2^(n+1)，随机数取上限
        st = c.stats["example.test"]
        self.assertEqual((st["requests"], st["retries"], st["status"]), (3, 2, {"429": 2, "200": 1}))

    def test_budget_and_client_errors_are_not_retried(self):
        ft, clock = FakeTransport(), Clock()
        ft.add("https://api.openalex.org/budget", 429, {"message": "Insufficient budget (test)"}, {"Retry-After": "49210"})
        ft.add("https://example.test/forbidden", 403, {"message": "forbidden (test)"})
        ft.add("https://example.test/missing", 404, "<!doctype html><title>404 Not Found</title><h1>Not Found</h1>",
               {"content-type": "text/html"})
        ft.add("https://example.test/long-wait", 429, {"message": "slow"}, {"Retry-After": "120"})
        c = make_client(ft, clock)
        with self.assertRaisesRegex(http.BudgetExhausted, "HTTP 429: Insufficient budget"):
            c.get_json("https://api.openalex.org/budget")
        with self.assertRaisesRegex(http.ClientError, "HTTP 403: forbidden"):
            c.get_json("https://example.test/forbidden")
        with self.assertRaises(http.NotFound) as cm:
            c.get_json("https://example.test/missing")
        self.assertEqual(str(cm.exception), "HTTP 404: 404 Not Found Not Found")        # HTML 去标签，不泄漏标记
        with self.assertRaises(http.BudgetExhausted) as cm:
            c.get_json("https://example.test/long-wait")
        self.assertEqual(cm.exception.retry_after, 120.0)
        self.assertEqual(clock.sleeps, [])

    def test_retry_after_is_honoured_and_network_errors_retried(self):
        ft, clock = FakeTransport(), Clock()
        url = "https://example.test/ra"
        ft.add(url, 503, {"error": "down"}, {"Retry-After": "7"})
        ft.add(url, 200, {"ok": 1})
        c = make_client(ft, clock)
        c.get_json(url)
        self.assertEqual(clock.sleeps, [7.0])
        url2 = "https://example.test/net"
        ft.queues[url2] = [(http.NetworkError("timed out", url=url2), None, None, None), (200, {"content-type": "application/json"}, b"{}", url2)]
        self.assertEqual(c.get_json(url2), {})
        self.assertEqual(clock.sleeps, [7.0, 2])

    def test_blocked_by_policy_fails_fast(self):
        ft, clock = FakeTransport(), Clock()
        url = "https://data.crosscite.org/x"
        ft.queues[url] = [(http.BlockedByPolicy("BLOCKED at data.crosscite.org (network policy, proxy 403)", url=url), None, None, None)]
        c = make_client(ft, clock)
        with self.assertRaisesRegex(http.BlockedByPolicy, "BLOCKED at data.crosscite.org"):
            c.get_json(url)
        self.assertEqual(len(ft.calls), 1)

    def test_s2_spacing_applies_to_retries_and_breaker_opens(self):
        ft, clock = FakeTransport(), Clock()
        url = "https://api.semanticscholar.org/graph/v1/paper/x"
        ft.add(url, 429, {"message": "Too Many Requests", "code": "429"})
        ft.add(url, 200, {"paperId": "p"})
        c = make_client(ft, clock)
        c.get_json(url)
        c.get_json(url)                                                       # 第二次请求与上一次间隔 ≥ 1.1 s
        gaps = [b - a for a, b in zip([t for t in _request_times(ft, clock)], _request_times(ft, clock)[1:])]
        self.assertTrue(all(g >= 1.1 - 1e-9 for g in gaps), gaps)
        # 熔断：连续 429 达到阈值
        ft2, clock2 = FakeTransport(), Clock()
        ft2.add(url, 429, {"message": "Too Many Requests", "code": "429"})
        pol = {"api.semanticscholar.org": http.HostPolicy(min_interval_s=0, max_attempts=3, breaker_consecutive=4)}
        c2 = make_client(ft2, clock2, policies=pol)
        with self.assertRaises(http.RateLimited):
            c2.get_json(url)                                                   # 3 次 429 后放弃
        with self.assertRaises(http.CircuitOpen):
            c2.get_json(url)                                                   # 第 4 次 429 后熔断，不再请求
        self.assertEqual(len(ft2.calls), 4)

    def test_rate_headers_are_summarized(self):
        ft, clock = FakeTransport(), Clock()
        url = "https://api.openalex.org/works?filter=x"
        ft.add(url, 200, {"meta": {"count": 1}, "results": []},
               {"X-Ratelimit-Credits-Used": "10", "X-Ratelimit-Remaining": "6738"})
        c = make_client(ft, clock)
        c.get_json(url)
        st = c.stats["api.openalex.org"]
        self.assertEqual((st["credits_used"], st["remaining"]), (10, "6738"))
        self.assertEqual(c.stats_summary()["mode"], "live")


def _request_times(ft, clock):
    # FakeTransport 不记时间；用 clock.sleeps 累加还原每次请求的时刻
    times, t = [], 1000.0
    for s in [0.0] + clock.sleeps:
        t += s
        times.append(t)
    return times[:len(ft.calls)]


class TestAuthAndRedirects(unittest.TestCase):
    def test_keys_go_only_to_their_hosts(self):
        ft, clock = FakeTransport(), Clock()
        ft.add("https://api.openalex.org/works/W1", 200, {"id": "W1"})
        ft.add("https://api.semanticscholar.org/graph/v1/paper/x", 200, {"paperId": "x"})
        ft.add("https://api.crossref.org/works/10.1/x", 200, {"status": "ok", "message": {"DOI": "10.1/x"}})
        c = make_client(ft, clock, env={"OPENALEX_API_KEY": "oa-secret", "S2_API_KEY": "s2-secret"})
        for u in ("https://api.openalex.org/works/W1", "https://api.semanticscholar.org/graph/v1/paper/x",
                  "https://api.crossref.org/works/10.1/x"):
            c.get_json(u)
        h = {call[1]: call[2] for call in ft.calls}
        self.assertEqual(h["https://api.openalex.org/works/W1"].get("Authorization"), "Bearer oa-secret")
        self.assertEqual(h["https://api.semanticscholar.org/graph/v1/paper/x"].get("x-api-key"), "s2-secret")
        self.assertNotIn("Authorization", h["https://api.crossref.org/works/10.1/x"])
        self.assertTrue(h["https://api.crossref.org/works/10.1/x"]["User-Agent"].startswith("novelty-probe/"))

    def test_follow_records_chain_and_upgrades_http(self):
        ft, clock = FakeTransport(), Clock()
        ft.add("https://doi.org/10.1108/x", 302, b"", {"Location": "http://www.emerald.com/a"})
        ft.add("https://www.emerald.com/a", 200, "<html><title>Page</title></html>", {"content-type": "text/html"})
        c = make_client(ft, clock)
        r = c.request("https://doi.org/10.1108/x", accept="text/html", errors_as_result=True)
        self.assertEqual((r.status, r.chain, r.upgraded), (200, [(302, "https://www.emerald.com/a")], ["https://www.emerald.com/a"]))
        self.assertEqual(r.final_url, "https://www.emerald.com/a")
        # 4xx 作为结果返回（核验落地页）
        ft.add("https://pub.test/403", 403, "<title>Just a moment...</title>", {"content-type": "text/html"})
        r = c.request("https://pub.test/403", accept="text/html", errors_as_result=True)
        self.assertEqual(r.status, 403)


class TestCacheAndReplay(unittest.TestCase):
    def test_cache_mode_hits_then_serves_stale_on_error(self):
        with tempfile.TemporaryDirectory() as d:
            ft, clock = FakeTransport(), Clock()
            url = "https://api.crossref.org/works/10.1/x?mailto=me@example.org"
            ft.add(url, 200, {"status": "ok", "message": {"DOI": "10.1/x"}})
            c = make_client(ft, clock, mode="cache", tmp=d)
            c.get_json(url)
            c.get_json(url)                                                    # 命中缓存，不再请求
            self.assertEqual(len(ft.calls), 1)
            self.assertEqual(c.stats["api.crossref.org"]["cache_hits"], 1)
            entry_files = list(Path(d, "cache").rglob("*.json"))
            self.assertEqual(len(entry_files), 1)
            text = entry_files[0].read_text(encoding="utf-8")
            self.assertNotIn("mailto", text)                                   # 密钥类参数不落盘
            # 过期后网络失败 → 用过期条目
            entry = json.loads(text)
            entry["meta"]["expires_at"] = "2000-01-01T00:00:00+00:00"
            entry_files[0].write_text(json.dumps(entry), encoding="utf-8")
            ft.queues[url] = [(503, {"content-type": "application/json"}, b'{"error":"down"}', url)]
            pol = {"api.crossref.org": http.HostPolicy(max_attempts=1)}
            c2 = make_client(ft, clock, mode="cache", tmp=d, policies=pol)
            r = c2.request(url)
            self.assertEqual(r.from_cache, "stale")
            self.assertTrue(r.warnings and "stale" in r.warnings[0])

    def test_record_then_replay_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            ft, clock = FakeTransport(), Clock()
            url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=a"
            ft.add(url, 429, {"message": "Too Many Requests", "code": "429"})
            ft.add(url, 200, {"total": 1, "token": None, "data": [{"paperId": "p"}]})
            cassette = Path(d) / "cassette.json"
            pol = {"api.semanticscholar.org": http.HostPolicy(min_interval_s=0)}
            rec = make_client(ft, clock, mode="record", tmp=d, cassette=str(cassette), policies=pol)
            self.assertEqual(rec.get_json(url)["total"], 1)                   # 429 → 重试 → 200（只有 200 被录）
            saved = json.loads(cassette.read_text(encoding="utf-8"))
            self.assertEqual([i["response"]["status"] for i in saved["interactions"]], [200])
            rep = make_client(FakeTransport(), Clock(), mode="replay", tmp=d, cassette=str(cassette))
            self.assertEqual(rep.get_json(url)["data"][0]["paperId"], "p")
            with self.assertRaisesRegex(http.ReplayMiss, "录制件中没有这个请求"):
                rep.get_json(url)                                              # 第二次：队列已空
            with self.assertRaises(http.ReplayMiss):
                rep.get_json("https://api.openalex.org/works?filter=y")
            self.assertEqual(rep.stats["api.semanticscholar.org"]["cache_hits"], 1)

    def test_cache_key_normalization(self):
        a = cache.cache_key("GET", "https://API.OpenAlex.org/works?per-page=2&filter=x&api_key=zzz")
        b = cache.cache_key("GET", "https://api.openalex.org:443/works?filter=x&per-page=2#frag")
        self.assertEqual(a, b)
        self.assertNotEqual(a, cache.cache_key("GET", "https://api.openalex.org/works?filter=x&per-page=3"))
        self.assertNotEqual(a, cache.cache_key("GET", "https://api.openalex.org/works?filter=x&per-page=2", accept="text/html"))


class TestPagination(unittest.TestCase):
    def test_cursor_and_token_with_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as d:
            ft, clock = FakeTransport(), Clock()
            base = "https://api.openalex.org/works"
            ft.add(base + "?filter=x&cursor=%2A", 200, {"meta": {"next_cursor": "c2"}, "results": [{"id": "W1"}]})
            ft.add(base + "?filter=x&cursor=c2", 200, {"meta": {"next_cursor": "c3"}, "results": [{"id": "W2"}]})
            ft.add(base + "?filter=x&cursor=c3", 200, {"meta": {"next_cursor": None}, "results": []})
            c = make_client(ft, clock, tmp=d)
            ck = Path(d) / "ck.json"
            pages = list(c.paginate(base, {"filter": "x"}, scheme=http.Cursor(), checkpoint=ck))
            self.assertEqual([len(items) for _, items in pages], [1, 1, 0])
            self.assertFalse(ck.exists())                                      # 完成后删除断点
            # 中断后续跑：先手工造一个断点
            ck.write_text(json.dumps({"url": base, "next": "c3", "pages": 2, "items": [{"id": "W1"}, {"id": "W2"}]}), encoding="utf-8")
            pages = list(c.paginate(base, {"filter": "x"}, scheme=http.Cursor(), checkpoint=ck))
            self.assertEqual(pages[0][0], {"_resumed": True, "pages": 2})
            self.assertEqual(len(pages[0][1]), 2)
            self.assertEqual(len(ft.calls), 4)                                 # 只多请求了最后一页
            # S2 token：失效令牌 → 从头开始
            s2 = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
            ft.add(s2 + "?query=q", 200, {"total": 2, "token": "t2", "data": [{"paperId": "a"}]})
            ft.add(s2 + "?query=q&token=stale", 400, {"error": "Invalid bulk token"})
            ft.add(s2 + "?query=q&token=t2", 200, {"total": 2, "token": None, "data": [{"paperId": "b"}]})
            ck2 = Path(d) / "ck2.json"
            ck2.write_text(json.dumps({"url": s2, "next": "stale", "pages": 1, "items": [{"paperId": "old"}]}), encoding="utf-8")
            pol = {"api.semanticscholar.org": http.HostPolicy(min_interval_s=0)}
            c2 = make_client(ft, clock, tmp=d, policies=pol)
            pages = list(c2.paginate(s2, {"query": "q"}, scheme=http.Token(), checkpoint=ck2))
            ids = [p["paperId"] for _, items in pages if items for p in items if "paperId" in p]
            self.assertEqual(ids, ["a", "b"])                                  # 失效令牌：丢弃断点里的旧条目，重新取全
            self.assertFalse(ck2.exists())


class TestSchemas(unittest.TestCase):
    def test_openalex_and_s2_shapes(self):
        good = {"meta": {"count": 1, "per_page": 2, "x_query": {"oql": "x", "oqo": {}}},
                "results": [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/x", "publication_year": 2024}]}
        self.assertEqual(schemas.openalex_list(good), [])
        bad = {"meta": {"count": "1"}, "results": [{"id": "W1", "doi": "10.1/x", "publication_year": "2024"}]}
        w = schemas.openalex_list(bad)
        self.assertTrue(any("meta.count" in x for x in w) and any("doi" in x for x in w) and any("publication_year" in x for x in w))
        self.assertEqual(schemas.s2_bulk({"total": 3, "token": None, "data": [{"paperId": "p", "abstract": None}]}), [])
        self.assertIn("batch returned 1 items for 2 ids", schemas.s2_batch([None], n_ids=2))
        self.assertEqual(schemas.crossref_agency({"message": {"agency": {"id": "datacite"}}}), [])
        self.assertTrue(schemas.crossref_work({"status": "ok", "message": {"title": "not a list"}}))

    def test_summarize_body(self):
        self.assertEqual(http.summarize_body(b'{"error": "Invalid bulk token"}', "application/json"), "Invalid bulk token")
        self.assertEqual(http.summarize_body(b"<html><title>404 Not Found</title></html>", "text/html"), "404 Not Found")
        self.assertEqual(http.summarize_body(b"Resource not found.", "text/plain"), "Resource not found.")


if __name__ == "__main__":
    unittest.main()
