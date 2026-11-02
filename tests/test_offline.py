#!/usr/bin/env python3
"""novelty-probe 离线自检：不联网、不改动仓库里的任何文件。

运行：python3 -m unittest discover -s tests -v

覆盖：
- 检索式文件的校验，以及到 OpenAlex / Semantic Scholar 两种语法的转换；
- 检索结果的字段提取、请求重试规则、检索主流程（模拟 API，写入临时目录）；
- 合并去重与候选排序；用仓库里已提交的原始结果重跑合并，须与已提交的合并结果逐字节一致；
- 作者查询（模拟 API）；
- DOI 核验（127.0.0.1 上的模拟服务器）；
- logrun 的日志写入与退出码；
- 仓库数据文件（检索式、证据表、CITATION.cff、LICENSE）的格式。
"""
import contextlib
import csv
import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.dont_write_bytecode = True     # 不在 scripts/ 下生成 __pycache__
sys.path.insert(0, str(SCRIPTS))   # authors.py 里有 `from search import get_json`
for _var in ("NO_PROXY", "no_proxy"):  # 模拟服务器在本机，不走代理
    os.environ[_var] = "127.0.0.1,localhost"
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}


def load(name):
    spec = importlib.util.spec_from_file_location(f"np_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


search, merge, verify, authors = load("search"), load("merge"), load("verify"), load("authors")


class MockServer:
    """在 127.0.0.1 的随机端口上起一个 HTTP 服务器，请求交给 handle(handler) 处理。"""

    def __init__(self, handle):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                handle(self)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def reply(h, code, body="", ctype="text/html; charset=utf-8", headers=()):
    h.send_response(code)
    for k, v in headers:
        h.send_header(k, v)
    h.send_header("Content-Type", ctype)
    h.end_headers()
    h.wfile.write(body.encode() if isinstance(body, str) else body)


def dead_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_script(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", env=CHILD_ENV)


# ---------- 检索式 ----------

class TestQueries(unittest.TestCase):
    def test_conversion_for_both_sources(self):
        q = '("large language models" OR "generative AI") AND (homogeniz* OR "collective diversity") AND scientist*'
        self.assertEqual(search.to_openalex(q),
                         '("large language models" OR "generative AI") AND (homogenization OR "collective diversity") AND scientists')
        self.assertEqual(search.to_s2_bulk(q),
                         '("large language models" | "generative AI") + (homogeniz* | "collective diversity") + scientist*')

    def test_unquoted_hyphen_becomes_phrase_for_s2(self):
        self.assertEqual(search.to_s2_bulk('(a-b OR "c-d") AND e'), '("a b" | "c-d") + e')

    def test_syntax_guards(self):
        for bad in ['"a" OR "b"', '(a OR (b OR c))', '(a AND b)', 'NOT a', '(a OR b', '() AND a']:
            with self.subTest(query=bad), self.assertRaises(ValueError):
                search.and_groups(bad)
        with self.assertRaises(ValueError):
            search.to_openalex('"a" AND foo*')      # 未登记的截断词
        with self.assertRaises(ValueError):
            search.to_openalex('"a, b" AND c')      # 逗号会破坏 OpenAlex 的 filter

    def test_repository_query_files_are_valid(self):
        for name in ("queries.json", "queries_v2.json"):
            with self.subTest(file=name):
                queries = search.load_queries(ROOT / "queries" / name)
                self.assertEqual([q["id"] for q in queries], [f"Q{i}" for i in range(1, 7)])
                for q in queries:
                    search.to_openalex(q["query"])
                    search.to_s2_bulk(q["query"])

    def test_load_queries_reports_problems(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "q.json"
            p.write_text(json.dumps([{"id": "q1", "query": "", "purpose": "concurent"},
                                     {"id": "Q2", "query": "a", "purpose": "method"},
                                     {"id": "Q2", "query": "b", "purpose": "method"}]), encoding="utf-8")
            with self.assertRaises(ValueError) as cm:
                search.load_queries(p)
            for part in ("'q1'", "缺少 query", "'concurent'", "id Q2 重复"):
                self.assertIn(part, str(cm.exception))
            p.write_text("```json\n[]\n```", encoding="utf-8")   # 助手把 JSON 包进了代码块
            with self.assertRaisesRegex(ValueError, "不是合法的 JSON"):
                search.load_queries(p)

    def test_dry_run_cli(self):
        r = run_script(SCRIPTS / "search.py", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("6/6 queries valid", r.stdout)

    def test_dry_run_flags_invalid_syntax_and_unknown_ids(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "q.json"
            p.write_text(json.dumps([{"id": "Q1", "query": '"a" OR "b"', "purpose": "method"}]), encoding="utf-8")
            r = run_script(SCRIPTS / "search.py", "--queries", p, "--dry-run")
            self.assertEqual(r.returncode, 1)
            self.assertIn("INVALID", r.stdout)
        r = run_script(SCRIPTS / "search.py", "--ids", "Q9", "--dry-run")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Q9", r.stderr)


# ---------- 检索结果与请求 ----------

class TestRecords(unittest.TestCase):
    def test_openalex_record(self):
        w = {"doi": "https://doi.org/10.48550/arXiv.0000.00001", "title": "T", "publication_year": 2024,
             "primary_location": {"source": {"display_name": "arXiv (Cornell University)"}},
             "abstract_inverted_index": {"world": [1], "Hello": [0]}}
        r = search.openalex_record(w, "Q1")
        self.assertEqual(list(r), ["title", "year", "doi", "arxiv_id", "venue", "abstract", "source_api", "query_id"])
        self.assertEqual((r["doi"], r["arxiv_id"], r["abstract"]), ("10.48550/arXiv.0000.00001", "0000.00001", "Hello world"))
        w2 = {"doi": None, "display_name": "T2", "locations": [{"pdf_url": "https://arxiv.org/pdf/math/0000001v2.pdf"}]}
        self.assertEqual(search.openalex_record(w2, "Q1")["arxiv_id"], "math/0000001")

    def test_s2_record(self):
        p = {"title": "P", "year": 2024, "externalIds": {"DOI": "10.0000/X", "ArXiv": "0000.00004v3"},
             "venue": "", "journal": {"name": "J"}}
        r = search.s2_record(p, "Q2")
        self.assertEqual((r["doi"], r["arxiv_id"], r["venue"], r["source_api"]), ("10.0000/X", "0000.00004", "J", "semanticscholar"))


class TestGetJson(unittest.TestCase):
    def setUp(self):
        self.calls = 0

        def handle(h):
            if h.path == "/budget":
                reply(h, 429, '{"message": "Insufficient budget (test)"}', "application/json", [("Retry-After", "49210")])
            elif h.path == "/forbidden":
                reply(h, 403, '{"message": "forbidden (test)"}', "application/json")
            elif h.path == "/flaky":
                self.calls += 1
                if self.calls <= 2:
                    reply(h, 429, '{"message": "busy"}', "application/json")
                else:
                    reply(h, 200, '{"ok": true}', "application/json")

        self.server = MockServer(handle)

    def tearDown(self):
        self.server.close()

    def test_retry_rules(self):
        slept = []
        with mock.patch("time.sleep", side_effect=slept.append):
            with self.assertRaisesRegex(RuntimeError, "HTTP 429: Insufficient budget"):
                search.get_json(self.server.url + "/budget")      # 要求等太久：不重试
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                search.get_json(self.server.url + "/forbidden")   # 其他错误：不重试
            self.assertEqual(slept, [])
            self.assertEqual(search.get_json(self.server.url + "/flaky"), {"ok": True})
        self.assertEqual(slept, [2, 4])


class TestSearchMain(unittest.TestCase):
    def test_writes_raw_files_and_applies_year_filter(self):
        work = {"doi": "https://doi.org/10.0000/w", "title": "W", "publication_year": 2024, "primary_location": None}
        paper = {"title": "P", "year": 2024, "externalIds": {"DOI": "10.0000/p"}, "venue": "V"}
        urls = []

        def fake_get_json(url, headers=None, retries=5):
            urls.append(url)
            return {"meta": {"count": 7}, "results": [work]} if "openalex" in url else {"total": 3, "data": [paper]}

        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "raw"
            with mock.patch.object(search, "ROOT", Path(d)), mock.patch.object(search, "RAW_DIR", raw), \
                    mock.patch.object(search, "get_json", fake_get_json), mock.patch("time.sleep"), \
                    mock.patch.object(sys, "argv", ["search.py", "--suffix", "_t"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(search.main(), 0)
            self.assertEqual(len(list(raw.glob("*_t.json"))), 12)
            data = json.loads((raw / "openalex_Q6_t.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"meta", "records"})
        self.assertEqual((data["meta"]["purpose"], data["meta"]["year_from"], data["meta"]["total_hits"]), ("concurrent", 2023, 7))
        self.assertTrue(any("from_publication_date%3A2023-01-01" in u for u in urls))
        self.assertTrue(any("year=2023-" in u for u in urls))


# ---------- 合并去重 ----------

def rec(i, src, qid, title, year, doi=None, arxiv=None, venue=None, abstract=None):
    return {"title": title, "year": year, "doi": doi, "arxiv_id": arxiv, "venue": venue, "abstract": abstract,
            "source_api": src, "query_id": qid, "_ref": f"{src}_{qid}#{i}",
            "_order": (merge.SOURCE_ORDER.index(src), merge.qnum(qid), i)}


class TestMerge(unittest.TestCase):
    @staticmethod
    def build_all(recs):
        roots_id, roots_all = merge.group(recs, False), merge.group(recs, True)
        groups = {}
        for i, root in enumerate(roots_all):
            groups.setdefault(root, []).append(i)
        return [merge.build(g, recs, roots_id) for g in groups.values()]

    def test_dedupe_rules(self):
        t = "A study of something with enough words"
        recs = [
            rec(1, "semanticscholar", "Q1", "Paper one title goes here long", 2024, doi="10.0000/J.1", arxiv="0000.00001", venue="Journal X"),
            rec(2, "openalex", "Q6", "Paper one title goes here long", 2023, doi="10.48550/arXiv.0000.00001", arxiv="0000.00001", venue="arXiv", abstract="longer abstract"),
            rec(3, "openalex", "Q2", "Case", 2020, doi="10.0000/ABC"),
            rec(4, "semanticscholar", "Q2", "Case", 2020, doi="10.0000/abc"),
            rec(5, "openalex", "Q3", t, 2022, doi="10.0000/D.5"),
            rec(6, "semanticscholar", "Q3", t, 2022),
            rec(7, "openalex", "Q4", "Editorial", 2021),
            rec(8, "semanticscholar", "Q4", "Editorial", 2021),
            rec(9, "openalex", "Q5", "OSF preprint version one", 2024, doi="10.31234/osf.io/abcde_v1"),
            rec(10, "openalex", "Q5", "OSF preprint second wording", 2025, doi="10.31234/osf.io/abcde"),
        ]
        out = self.build_all(recs)
        get = lambda ref: next(x for x in out if ref in x["raw_refs"])  # noqa: E731
        self.assertEqual(len(out), 6)
        a = get("openalex_Q6#2")   # arXiv ID 相同；优先期刊 DOI；年份取最早
        self.assertEqual((a["doi"], a["arxiv_id"], a["alt_ids"], a["id_status"], a["year"]), ("10.0000/J.1", "0000.00001", [], "DOI", 2023))
        self.assertEqual((a["hits"], a["n_queries"], a["n_sources"], a["mean_rank"]), (2, 2, 2, 1.5))
        self.assertEqual(get("openalex_Q2#3")["raw_refs"], ["openalex_Q2#3", "semanticscholar_Q2#4"])  # DOI 不分大小写
        self.assertTrue(get("semanticscholar_Q3#6")["title_linked"])                                    # 只靠标题合并
        self.assertIsNot(get("openalex_Q4#7"), get("semanticscholar_Q4#8"))                             # 短标题不合并
        self.assertEqual(get("openalex_Q4#7")["id_status"], "UNVERIFIED")
        osf = get("openalex_Q5#9")                                                                       # 预印本版本 DOI
        self.assertEqual((osf["raw_refs"], osf["title_linked"]), (["openalex_Q5#9", "openalex_Q5#10"], False))

    def test_candidate_ordering(self):
        def c(mid, hits, nq, ns, refs):
            return {"merged_id": mid, "hits": hits, "n_queries": nq, "n_sources": ns, "raw_refs": refs}
        cands = [c("M5", 1, 1, 1, ["openalex_Q1#1"]),
                 c("M4", 2, 1, 2, ["openalex_Q1#9", "semanticscholar_Q1#9"]),
                 c("M3", 2, 2, 1, ["openalex_Q1#20", "openalex_Q2#20"]),
                 c("M2", 2, 1, 2, ["openalex_Q1#2", "semanticscholar_Q1#3"]),
                 c("M1", 3, 2, 2, ["openalex_Q1#25", "openalex_Q2#25", "semanticscholar_Q1#25"])]
        self.assertEqual([x["merged_id"] for x in sorted(cands, key=merge.candidate_key)], ["M1", "M3", "M2", "M4", "M5"])

    def test_raw_files_selects_by_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("openalex_Q1.json", "semanticscholar_Q12.json", "openalex_Q1_v2.json", "merged.json", "openalex_X1.json"):
                (Path(d) / name).write_text("{}", encoding="utf-8")
            with mock.patch.object(merge, "RAW_DIR", Path(d)):
                self.assertEqual([p.name for p in merge.raw_files("")], ["openalex_Q1.json", "semanticscholar_Q12.json"])
                self.assertEqual([p.name for p in merge.raw_files("_v2")], ["openalex_Q1_v2.json"])

    def test_reproduces_committed_merge_outputs(self):
        """用仓库里已提交的 results/raw 重跑合并，须与已提交的 merged*.json、candidates*.csv 一致。"""
        for suffix in ("", "_v2"):
            with self.subTest(round=suffix or "v1"), tempfile.TemporaryDirectory() as d:
                with mock.patch.object(merge, "OUT_DIR", Path(d)), mock.patch.object(sys, "argv", ["merge.py", "--suffix", suffix]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    merge.main()
                new = json.loads((Path(d) / f"merged{suffix}.json").read_text(encoding="utf-8"))
                old = json.loads((ROOT / "results" / "merged" / f"merged{suffix}.json").read_text(encoding="utf-8"))
                self.assertEqual(new["records"], old["records"])
                self.assertEqual(new["meta"]["counts"], old["meta"]["counts"])
                self.assertEqual((Path(d) / f"candidates{suffix}.csv").read_bytes(),
                                 (ROOT / "results" / "merged" / f"candidates{suffix}.csv").read_bytes())


# ---------- 作者 ----------

class TestAuthors(unittest.TestCase):
    def test_authors_from_fake_openalex(self):
        def fake_get_json(url, headers=None, retries=5):
            self.assertIn("/works/doi:10.0000/a", url)
            return {"id": "https://openalex.org/W1", "display_name": "Alpha Paper Title",
                    "authorships": [{"author": {"display_name": "A One"}}, {"author": {}, "raw_author_name": "B Two"}]}

        with tempfile.TemporaryDirectory() as d:
            cand, out = Path(d) / "c.csv", Path(d) / "authors.json"
            with cand.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["rank", "merged_id", "doi", "title"])
                w.writeheader()
                w.writerow({"rank": 1, "merged_id": "M001", "doi": "10.0000/a", "title": "Alpha paper title"})
                w.writerow({"rank": 2, "merged_id": "M002", "doi": "", "title": "No DOI here"})
            with mock.patch.object(authors, "get_json", fake_get_json), \
                    mock.patch.object(sys, "argv", ["authors.py", "--top", "2", "--candidates", str(cand), "--out", str(out)]), \
                    contextlib.redirect_stdout(io.StringIO()):
                authors.main()
            recs = json.loads(out.read_text(encoding="utf-8"))["records"]
        self.assertEqual((recs[0]["authors"], recs[0]["title_matches"]), (["A One", "B Two"], True))
        self.assertIsNone(recs[1]["authors"])
        self.assertIn("no DOI", recs[1]["error"])


# ---------- DOI 核验 ----------

class TestVerify(unittest.TestCase):
    LONG = ("A temporal adaptive dictionary-constrained LDA and Bi-calibrated dual granularity DTM framework "
            "for dynamic topic evolution analysis in academic papers")

    def setUp(self):
        self.retry_calls, self.openalex_calls = 0, []
        dead = f"http://127.0.0.1:{dead_port()}/x"
        csl_type = verify.CSL_ACCEPT

        def csl(title):
            return json.dumps({"title": title, "container-title": "J", "issued": {"date-parts": [[2024]]},
                               "author": [{"family": "Doe"}]})

        def handle(h):
            path, wants_csl = h.path, csl_type in (h.headers.get("Accept") or "")
            if path.startswith("/10.0000/"):
                key = path.rsplit("/", 1)[1]
                if key == "missing":
                    return reply(h, 404, "<title>Not found</title>")
                if wants_csl and key != "datacite":
                    return reply(h, 302, headers=[("Location", f"/csl/{key}")])
                landing = {"ok": "/page/ok", "mismatch": "/page/forbidden", "retry": dead, "long": dead, "en": "/page/en",
                           "datacite": "/page/ok"}
                if wants_csl and key == "datacite":   # 像 arXiv DOI 被转到不可达的 data.crosscite.org
                    return reply(h, 302, headers=[("Location", dead)])
                return reply(h, 302, headers=[("Location", landing[key])])
            if path.startswith("/works/doi:"):        # OpenAlex 备用核验
                self.openalex_calls.append(path)
                if "/datacite" in path:
                    return reply(h, 200, json.dumps({"id": "W1", "display_name": "DataCite Paper"}), "application/json")
                return reply(h, 404, json.dumps({"error": "Not found"}), "application/json")
            if path == "/csl/retry":
                self.retry_calls += 1
                return reply(h, 429) if self.retry_calls <= 2 else reply(h, 200, csl("Retry <i>Paper</i>"), csl_type)
            titles = {"/csl/ok": "Test Paper One", "/csl/mismatch": "Completely Different Work",
                      "/csl/long": self.LONG, "/csl/en": "An English Test Paper"}
            if path in titles:
                return reply(h, 200, csl(titles[path]), csl_type)
            pages = {"/page/ok": (200, "<title>Test Paper One | Journal X</title>"),
                     "/page/forbidden": (403, "<title>Just a moment...</title>"),
                     "/page/en": (200, "<title>An English Test Paper</title>")}
            code, body = pages.get(path, (404, ""))
            reply(h, code, body)

        self.server = MockServer(handle)
        self.patches = [mock.patch.object(verify, "DOI_RESOLVER", self.server.url + "/"),
                        mock.patch.object(verify, "OPENALEX_WORKS", self.server.url + "/works/doi:"),
                        mock.patch.object(verify, "PAUSE", 0), mock.patch("time.sleep"),
                        mock.patch.dict(os.environ, {"http_proxy": "", "HTTP_PROXY": ""})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.server.close()

    def run_table(self, header, rows, *flags):
        with tempfile.TemporaryDirectory() as d:
            table = Path(d) / "t.md"
            sep = "|---" * (header.count("|") - 1) + "|"
            table.write_text("\n".join(["intro", header, sep, *rows, "", "tail"]) + "\n", encoding="utf-8")
            with mock.patch.object(sys, "argv", ["verify.py", "--table", str(table), *flags]), \
                    contextlib.redirect_stdout(io.StringIO()):
                rc = verify.main()
            lines = table.read_text(encoding="utf-8").splitlines()
        self.assertEqual((lines[0], lines[-1]), ("intro", "tail"))   # 表外内容不变
        rows = [verify.split_row(l) for l in lines if l.startswith("| ")]
        return rc, {r[0]: r[-1] for r in rows if r[0].isdigit()}

    def test_crossref_and_landing_results(self):
        rc, cells = self.run_table("| rank | 题目 | DOI/arXiv | verified |", [
            "| 1 | Test Paper One | doi:10.0000/ok · arXiv:0000.00001 | 待核验 |",
            "| 2 | Mismatch Case | doi:10.0000/mismatch | 待核验 |",
            "| 3 | Retry Paper | doi:10.0000/retry | 待核验 |",
            f"| 4 | {self.LONG} | doi:10.0000/long | 待核验 |",
            "| 5 | Missing | doi:10.0000/missing | 待核验 |",
            "| 6 | Only arXiv | arXiv:0000.00006 | 待核验 |",
        ])
        self.assertEqual(cells["1"], "Crossref HTTP 200 · 题目一致 · Test Paper One；落地页 HTTP 200 (127.0.0.1) · Test Paper One \\| Journal X")
        self.assertEqual(cells["2"], "Crossref HTTP 200 · 题目不一致 · Completely Different Work；落地页 HTTP 403 (127.0.0.1) · Just a moment...")
        self.assertTrue(cells["3"].startswith("Crossref HTTP 200 · 题目一致 · Retry Paper；落地页 ERROR at http://127.0.0.1:"))
        self.assertEqual(self.retry_calls, 3)                                      # 两次 429 后成功
        self.assertTrue(cells["4"].startswith("Crossref HTTP 200 · 题目一致 · A temporal adaptive"))  # 长题目用全文比对
        self.assertIn("…；", cells["4"])                                            # 只在显示时截短
        self.assertEqual(cells["5"], "Crossref HTTP 404 (127.0.0.1)；OpenAlex HTTP 404 (未收录该 DOI)；"
                                     "落地页 HTTP 404 (127.0.0.1) · Not found")    # Crossref 失败后查 OpenAlex，也查不到
        self.assertEqual(cells["6"], "UNVERIFIED")
        self.assertEqual(len(self.openalex_calls), 1)                               # Crossref 成功的行不查 OpenAlex
        self.assertEqual(rc, 1)                                                     # rank 5 两项元数据核验都失败

    def test_openalex_fallback_and_no_landing(self):
        rc, cells = self.run_table("| rank | 题目 | DOI/arXiv | verified |",
                                   ["| 1 | DataCite Paper | doi:10.0000/datacite · arXiv:0000.00007 | 待核验 |"], "--no-landing")
        self.assertTrue(cells["1"].startswith("Crossref ERROR at http://127.0.0.1:"), cells["1"])
        self.assertTrue(cells["1"].endswith("；OpenAlex · 题目一致 · DataCite Paper；落地页 skipped"), cells["1"])
        self.assertEqual(rc, 0)                                                     # OpenAlex 核验通过

    def test_https_to_http_redirect_is_upgraded(self):
        rec = verify.RecordingRedirects()
        req = verify.urllib.request.Request("https://doi.org/10.1108/x")
        new = rec.redirect_request(req, None, 302, "Found", {}, "http://www.emerald.com/a")
        self.assertEqual(new.full_url, "https://www.emerald.com/a")
        self.assertEqual(verify.hops({"chain": rec.chain, "upgraded": rec.upgraded}), "302 www.emerald.com (http→https)")
        local = verify.urllib.request.Request("http://127.0.0.1:1/10.0000/ok")   # 原本就是 http 的不改
        self.assertEqual(rec.redirect_request(local, None, 302, "Found", {}, "http://127.0.0.1:1/p").full_url,
                         "http://127.0.0.1:1/p")

    def test_english_title_header(self):
        rc, cells = self.run_table("| rank | Authors | Year | Title | DOI/arXiv | verified |",
                                   ["| 1 | A | 2025 | An English Test Paper | doi:10.0000/en | pending |"])
        self.assertTrue(cells["1"].startswith("Crossref HTTP 200 · 题目一致 · An English Test Paper"))
        self.assertEqual(rc, 0)


# ---------- logrun ----------

class TestLogrun(unittest.TestCase):
    def test_logs_command_and_passes_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "scripts").mkdir()
            (Path(d) / "logs").mkdir()
            logrun = Path(d) / "scripts" / "logrun.py"
            shutil.copy(SCRIPTS / "logrun.py", logrun)   # 在临时副本里运行，不写仓库的 RUN_LOG
            r = run_script(logrun, "T9 test", "--", sys.executable, "-c", "import sys; print('hello 你好'); sys.exit(3)")
            self.assertEqual(r.returncode, 3)
            self.assertIn("hello 你好", r.stdout)
            log = (Path(d) / "logs" / "RUN_LOG.md").read_text(encoding="utf-8")
            for part in ("] T9 test", "退出码 3", "hello 你好"):
                self.assertIn(part, log)
            self.assertEqual(run_script(logrun, "no command", "--").returncode, 1)


# ---------- 仓库数据文件 ----------

class TestRepositoryData(unittest.TestCase):
    FACETS = ["研究问题", "作用机制", "研究情境", "数据与方法", "预期发现"]

    def test_evidence_tables(self):
        for name in ("evidence_table.md", "evidence_table_v2.md"):
            with self.subTest(file=name):
                lines = (ROOT / "evidence" / name).read_text(encoding="utf-8").splitlines()
                h = next(i for i, l in enumerate(lines) if l.startswith("| rank |"))
                cols = verify.split_row(lines[h])
                rows = [verify.split_row(l) for l in lines[h + 2:] if l.startswith("| ") and verify.split_row(l)[0].isdigit()]
                self.assertTrue({"DOI/arXiv", "verified", *self.FACETS} <= set(cols))
                self.assertEqual(len(rows), 10)
                for r in rows:
                    self.assertTrue(all(r[cols.index(f)] in {"overlap", "differ", "unknown"} for f in self.FACETS))
                    self.assertRegex(r[cols.index("verified")], r"^(Crossref |UNVERIFIED)")

    def test_citation_and_license(self):
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        for key in ("cff-version: 1.2.0", "title:", "authors:", "orcid:", "license: MIT"):
            self.assertIn(key, cff)
        self.assertTrue((ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License"))


if __name__ == "__main__":
    unittest.main()
