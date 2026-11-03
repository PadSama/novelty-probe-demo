#!/usr/bin/env python3
"""阶段 3：检索式语法树（novelty_probe/query.py）与数据源（novelty_probe/sources/）的离线测试。不联网。

- 基准对照：示例检索式与边界写法的解析结果、OpenAlex 与 S2 检索串，与重构前逐字节相同（tests/fixtures/query_golden.json）；
- 错误码：每一类写法错误有固定错误码和位置，中英文说明；
- 往返：随机生成（固定种子）的合法检索式，规范写法再解析得到同一棵树；序列化不丢词；
- OpenAlex 解析核对：真实解析树通过，分组被改动的解析树被拦下（录制件 search_not.json）；
- Crossref：录制件回放（search_crossref.json），保存的记录都满足检索式，默认配置下不启用；
- 请求估算与额度预警；加一个数据源只需一个模块（用临时登记的假数据源验证）；三个来源的合并。
"""
import contextlib
import copy
import io
import json
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import EXAMPLE, ROOT, load  # noqa: E402

from novelty_probe import config, i18n, query as Q, sources  # noqa: E402
from novelty_probe.sources import openalex as oa_mod  # noqa: E402
from novelty_probe.sources.common import strip_markup  # noqa: E402
from novelty_probe.text import Doc, query_match  # noqa: E402

search, merge = load("search"), load("merge")
FIX = ROOT / "tests" / "fixtures"
CASSETTES = FIX / "cassettes"
GOLDEN = json.loads((FIX / "query_golden.json").read_text(encoding="utf-8"))


def run_main(module, argv):
    out = io.StringIO()
    with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
        rc = module.main()
    return rc, out.getvalue()


def replay_crossref(test, queries, ids=None, max_records=40):
    """开启 Crossref（各取 max_records 条），从录制件回放 search.py；返回 {检索式 id: 输出文件内容}。"""
    d = tempfile.mkdtemp()
    test.addCleanup(shutil.rmtree, d, True)
    cfg = Path(d) / "novelty-probe.json"
    cfg.write_text(json.dumps({"sources": {"crossref": {"enabled": True, "max_records": max_records}}}), encoding="utf-8")
    raw = Path(d) / "raw"
    argv = ["search.py", "--queries", str(queries), "--sources", "crossref", "--suffix", "_rec", "--config", str(cfg),
            "--cache-dir", str(Path(d) / "cache"), "--http-mode", "replay", "--cassette", str(CASSETTES / "search_crossref.json")]
    if ids:
        argv += ["--ids", ids]
    with mock.patch.object(search, "RAW_DIR", raw):
        rc, out = run_main(search, argv)
    test.assertEqual(rc, 0, out)
    return {p.stem.split("_")[1]: json.loads(p.read_text(encoding="utf-8")) for p in sorted(raw.glob("crossref_*.json"))}


class TestGolden(unittest.TestCase):
    def test_outputs_match_the_pre_refactor_baseline(self):
        tr = GOLDEN["truncation"]
        for it in GOLDEN["items"]:
            with self.subTest(item=f"{it['source']} {it['id']}"):
                q = Q.parse(it["query"])
                self.assertEqual(q.lists(), (it["include"], it["exclude"]))
                self.assertEqual(sources.REGISTRY["semanticscholar"].serialize(q, tr), it["semanticscholar"])
                if "openalex" in it:
                    self.assertEqual(sources.REGISTRY["openalex"].serialize(q, tr), it["openalex"])
                else:
                    with self.assertRaises(Q.QueryError) as cm:
                        sources.REGISTRY["openalex"].serialize(q, tr)
                    self.assertEqual(cm.exception.code, it["openalex_error_code"])
                # 旧接口照常可用
                self.assertEqual(search.parse_query(it["query"]), (it["include"], it["exclude"]))
                self.assertEqual(search.to_s2_bulk(it["query"]), it["semanticscholar"])


class TestErrorCodes(unittest.TestCase):
    CASES = [  # (检索式, 错误码, 出错位置（从 0 起）)
        ("(a OR (b))", "Q101", 6), ("a) AND b", "Q102", 1), ("a AND (b OR c", "Q102", 6), ("(a AND b)", "Q103", 3),
        ("a OR b", "Q104", 2), ("NOT a AND b", "Q105", 0), ("a AND (NOT b)", "Q106", 7), ("a AND NOT b NOT c", "Q106", 12),
        ("a and b", "Q107", 2), ("a AND -b", "Q108", 6), ("() AND a", "Q109", 1), ("a AND", "Q109", 5),
        ("a AND AND b", "Q109", 6), ("a AND NOT b AND NOT", "Q109", 19), ("a, b AND c", "Q111", 1),
        ('"x, y" AND z', "Q111", 2), ('"open quote AND x', "Q112", 0), ('"" AND x', "Q113", 0),
        ("sci*ence AND x", "Q114", 3), ("* AND x", "Q114", 0), ("(a b) AND c", "Q115", 3), ("a b AND c", "Q116", 2),
        ("(a) (b)", "Q116", 4), ("(OR a) AND b", "Q117", 1), ("(a OR) AND b", "Q117", 5),
    ]

    def tearDown(self):
        i18n.set_language("zh")

    def test_codes_and_positions(self):
        for text, code, pos in self.CASES:
            with self.subTest(query=text), self.assertRaises(Q.QueryError) as cm:
                Q.parse(text)
            self.assertEqual((cm.exception.code, cm.exception.pos), (code, pos))
            self.assertIn(f"（{code}，第 {pos + 1} 个字符）", str(cm.exception))

    def test_query_error_is_a_value_error_and_speaks_english(self):
        i18n.set_language("en")
        with self.assertRaises(ValueError) as cm:
            search.parse_query("(a b) AND c")
        self.assertEqual(str(cm.exception), "Terms inside parentheses must be joined by OR (Q115, at character 4)")

    def test_unregistered_truncation_is_a_serializer_error(self):
        q = Q.parse('"a" AND theor*')                                    # 写法本身合法
        self.assertEqual(sources.REGISTRY["semanticscholar"].serialize(q, {}), '"a" + theor*')  # S2 原生支持截断
        for name in ("openalex", "crossref"):
            with self.subTest(source=name), self.assertRaises(Q.QueryError) as cm:
                sources.REGISTRY[name].serialize(q, {})
            self.assertEqual((cm.exception.code, cm.exception.pos), ("Q201", 8))

    def test_dry_run_marks_the_position(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "q.json"
            f.write_text(json.dumps([{"id": "Q1", "query": '("generative AI" ChatGPT) AND x', "purpose": "component"}]),
                         encoding="utf-8")
            rc, out = run_main(search, ["search.py", "--dry-run", "--queries", str(f)])
        self.assertEqual(rc, 1)
        lines = out.splitlines()
        i = next(k for k, l in enumerate(lines) if "INVALID" in l)
        self.assertIn("Q115", lines[i])
        self.assertEqual(lines[i + 2].index("^") - len("         "), lines[i + 1].index("ChatGPT") - len("  query: "))


class TestRoundTrip(unittest.TestCase):
    WORDS = ["AI", "science", "LLM", "diversity", "economists", "bibliometric*", "scientist*", "state-of-the-art"]
    PHRASES = ['"generative AI"', '"large language models"', '"topic diversity"', '"AI-assisted writing"']

    def random_query(self, rng):
        def group(negated):
            terms = rng.sample(self.WORDS + self.PHRASES, rng.randint(1, 3))
            paren = len(terms) > 1 or rng.random() < 0.3
            pad = " " * rng.randint(0, 2)
            body = f" {pad}OR{pad} ".join(terms)
            text = f"({pad}{body}{pad})" if paren else body
            return ("NOT " + text) if negated else text
        include = [group(False) for _ in range(rng.randint(1, 4))]
        exclude = [group(True) for _ in range(rng.randint(0, 2))]
        return " AND ".join(include + exclude)

    def test_canonical_round_trip_and_serializers_keep_every_term(self):
        rng = random.Random(20261103)
        tr = {"bibliometric*": "bibliometrics", "scientist*": "scientists"}
        for _ in range(300):
            text = self.random_query(rng)
            with self.subTest(query=text):
                q = Q.parse(text)
                again = Q.parse(q.canonical())
                self.assertEqual(again.lists(), q.lists())
                self.assertEqual([g.negated for g in again.groups], [g.negated for g in q.groups])
                self.assertEqual(Q.parse(again.canonical()).canonical(), again.canonical())
                s2 = sources.REGISTRY["semanticscholar"].serialize(q, tr)
                oa = sources.REGISTRY["openalex"].serialize(q, tr)
                for term in q.terms() + q.terms(negated=True):
                    s2_form = ('"' + term.raw.replace("-", " ") + '"') if (term.kind != "phrase" and "-" in term.raw) else term.raw
                    self.assertIn(s2_form, s2)
                    self.assertIn(tr.get(term.raw, term.raw), oa)
                self.assertEqual(s2.count("+ -"), len(q.exclude))

    def test_evaluate(self):
        q = Q.parse('("generative AI" OR LLM*) AND diversity AND NOT ("narrow AI")')
        self.assertTrue(Q.evaluate(q, Doc("LLMs reduce diversity", "")))
        self.assertTrue(Q.evaluate(q, Doc("Generative AI and the diversity of ideas", None)))
        self.assertFalse(Q.evaluate(q, Doc("Generative AI", "no second group here")))
        self.assertFalse(Q.evaluate(q, Doc("Narrow AI, LLMs and diversity", "")))


class TestOpenAlexInterpretation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cas = json.loads((CASSETTES / "search_not.json").read_text(encoding="utf-8"))
        cls.api_meta = json.loads(cas["interactions"][0]["response"]["body"])["meta"]
        cls.sent = ('(narrowing OR "topic diversity" OR "topic concentration" OR "research diversification") AND '
                    '(economists OR "economic research" OR "management research" OR "business research") AND '
                    'NOT ("narrow AI" OR "narrow artificial intelligence")')

    def check(self, mutate=None):
        m = copy.deepcopy(self.api_meta)
        if mutate:
            mutate(m["x_query"]["oqo"]["filter_rows"])
        return oa_mod.check_interpretation(self.sent, m)

    def test_real_tree_passes(self):
        self.assertEqual(self.check(), [])

    def test_changed_groups_are_blocked(self):
        mutations = {
            "negation dropped": lambda r: r[0].pop("is_negated"),
            "term moved between groups": lambda r: r[3]["filters"].append(r[2]["filters"].pop()),
            "OR group flattened into AND rows": lambda r: r.extend(r.pop(2)["filters"]),
            "extra negated term": lambda r: r.append({"column_id": "title_and_abstract.search", "value": "economics",
                                                     "operator": "has", "is_negated": True}),
        }
        for label, mutate in mutations.items():
            with self.subTest(case=label), self.assertRaisesRegex(RuntimeError, "分组与发送的不同"):
                self.check(mutate)

    def test_equivalent_forms_and_unknown_shapes(self):
        negated_group = {"join": "or", "is_negated": True, "filters": [
            {"column_id": "title_and_abstract.search", "value": '"narrow AI"', "operator": "has"},
            {"column_id": "title_and_abstract.search", "value": '"narrow artificial intelligence"', "operator": "has"}]}
        self.assertEqual(self.check(lambda r: r.__setitem__(slice(0, 2), [negated_group])), [])   # NOT (a OR b) = NOT a AND NOT b
        self.assertEqual(self.check(lambda r: r.append({"column_id": "from_publication_date", "value": "2023-01-01"})), [])
        warnings = self.check(lambda r: r.append({"join": "and", "filters": []}))
        self.assertEqual(len(warnings), 1)
        self.assertIn("无法识别", warnings[0])

    def test_quoted_operators_still_abort(self):
        meta = {"x_query": {"oql": 'get works with (a "OR" b "AND" c)'}}
        with self.assertRaisesRegex(RuntimeError, "运算符当成了检索词"):
            oa_mod.check_interpretation("a AND b", meta)

    def test_replay_search_with_not(self):
        """v2b 的 Q2（含 NOT；2026-11-03 录制）：从录制件回放，解析核对通过。检索式写在测试里，不依赖项目目录的数据。"""
        q2 = ('(narrowing OR "topic diversity" OR "topic concentration" OR "research diversification") AND '
              '(economist* OR "economic research" OR "management research" OR "business research") AND '
              'NOT ("narrow AI" OR "narrow artificial intelligence")')
        with tempfile.TemporaryDirectory() as d:
            raw, f = Path(d) / "raw", Path(d) / "q.json"
            f.write_text(json.dumps([{"id": "Q2", "query": q2, "purpose": "component"}]), encoding="utf-8")
            argv = ["search.py", "--queries", str(f), "--sources", "openalex", "--suffix", "_rec",
                    "--cache-dir", str(Path(d) / "cache"), "--http-mode", "replay", "--cassette", str(CASSETTES / "search_not.json")]
            with mock.patch.object(search, "RAW_DIR", raw):
                rc, out = run_main(search, argv)
            self.assertEqual(rc, 0, out)
            data = json.loads((raw / "openalex_Q2_rec.json").read_text(encoding="utf-8"))
        self.assertEqual(data["meta"]["warnings"], [])
        self.assertEqual(len(data["records"]), 25)
        self.assertEqual(data["meta"]["total_hits"], 2756)


class TestCrossref(unittest.TestCase):
    def test_kept_records_satisfy_the_query(self):
        res = replay_crossref(self, FIX / "crossref_queries.json")
        self.assertEqual({k: len(v["records"]) for k, v in res.items()}, {"Q1": 1, "Q2": 6, "Q3": 1})
        self.assertEqual(res["Q1"]["records"][0]["doi"], "10.1145/3635636.3656204")
        self.assertEqual(res["Q3"]["meta"]["pool"]["skipped_types"], 36)              # 审稿意见（peer-review）不收
        for qid, data in res.items():
            meta = data["meta"]
            inc, exc = Q.parse(meta["query_original"]).lists()
            for r in data["records"]:
                self.assertTrue(query_match(inc, Doc(r["title"], r["abstract"]), exc), (qid, r["title"]))
                self.assertIsNone(r["arxiv_id"])
                self.assertEqual(r["source_api"], "crossref")
            self.assertEqual(meta["warnings"], [])
            self.assertTrue(meta["lossy"])
            self.assertIn("bag of words", meta["conversion"])
        self.assertNotIn("&lt;", json.dumps(res["Q2"]["records"], ensure_ascii=False))   # 题目里转义过的标签已去掉

    def test_bag_of_words_queries_from_the_tutorial_keep_nothing(self):
        """实测：教程的长检索式在 Crossref 前 40 条里没有满足检索式的记录（常见词占满前列）。"""
        res = replay_crossref(self, EXAMPLE / "queries" / "queries.json", "Q1,Q3,Q4")
        for qid, data in res.items():
            self.assertEqual((len(data["records"]), data["meta"]["pool"]["conforming"]), (0, 0), qid)

    def test_off_by_default_and_serialization(self):
        self.assertEqual(sources.enabled(config.defaults()), ["openalex", "semanticscholar"])
        rc, out = run_main(search, ["search.py", "--dry-run", "--queries", str(EXAMPLE / "queries" / "queries.json")])
        self.assertEqual(rc, 0)
        self.assertNotIn("crossref:", out)
        q = Q.parse('("large language models" OR LLM) AND homogeniz* AND NOT ("narrow AI")')
        self.assertEqual(sources.REGISTRY["crossref"].serialize(q, {"homogeniz*": "homogenization"}),
                         "large language models LLM homogenization")
        self.assertEqual(strip_markup("&lt;strong&gt;Generative&lt;/strong&gt; AI <jats:p>x</jats:p>"), "Generative AI x")


class TestRequestPlan(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("zh")

    def test_plan_and_line(self):
        cfg = config.defaults()
        plan = search.request_plan(cfg, ["openalex", "semanticscholar"], 6)
        self.assertEqual(plan, {"openalex": {"requests": 6, "credits": 60}, "semanticscholar": {"requests": 18, "credits": 0}})
        cfg["sources"]["crossref"]["max_records"] = 2500
        self.assertEqual(search.request_plan(cfg, ["crossref"], 2), {"crossref": {"requests": 6, "credits": 0}})
        i18n.set_language("en")
        self.assertEqual(search.plan_line(plan), "Request estimate (upper bound): openalex at most 6 requests "
                                                 "(about 60 OpenAlex credits); semanticscholar at most 18 requests")

    def test_dry_run_prints_the_plan(self):
        rc, out = run_main(search, ["search.py", "--dry-run", "--queries", str(EXAMPLE / "queries" / "queries.json")])
        self.assertIn("请求估算（上限）：openalex 最多 6 个请求（OpenAlex 约 60 credits）；semanticscholar 最多 18 个请求", out)

    def test_credit_warning_before_running_out(self):
        good = {"meta": {"count": 1, "x_query": {"oql": "get works with a"}}, "results": []}

        def fake(url, *a, **k):
            search.default_client().stats["api.openalex.org"] = {"remaining": "15"}   # 只够 1 个请求（10 credits）
            return good
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "q.json"
            f.write_text(json.dumps([{"id": f"Q{i}", "query": "a", "purpose": "component"} for i in (1, 2, 3)]), encoding="utf-8")
            with mock.patch.object(search, "get_json", fake), mock.patch.object(search, "RAW_DIR", Path(d) / "raw"):
                rc, out = run_main(search, ["search.py", "--queries", str(f), "--sources", "openalex"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.count("OpenAlex 剩余额度 15 credits"), 1)
        self.assertIn("余下 2 个请求（约 20 credits）", out)


class FakeSource(sources.Source):
    """加一个数据源需要的全部代码：序列化、检索、记录转换（这里用固定数据代替网络）。"""
    name = "fake"
    conversion = "fake: terms joined by spaces"

    def serialize(self, query, truncation):
        return " ".join(t.text for t in query.terms())

    def unsupported(self, query):
        return ["NOT is not supported"] if query.exclude else []

    def search(self, item, year_from, ctx):
        data = ctx.fetch("https://fake.example/search?q=" + self.serialize(Q.parse(item["query"]), ctx.truncation))
        records = [{"title": w["t"], "year": 2024, "doi": w["doi"], "arxiv_id": None, "venue": None, "abstract": w["a"],
                    "source_api": self.name, "query_id": item["id"]} for w in data["hits"]][:ctx.top_n]
        return {"conversion": self.conversion, "query_sent": "x", "total_hits": len(data["hits"]), "warnings": []}, records


class TestExtensibility(unittest.TestCase):
    def setUp(self):
        sources.register(FakeSource())
        self.addCleanup(sources.unregister, "fake")

    def test_new_source_runs_through_search_and_merge_without_changing_them(self):
        hits = {"hits": [{"t": "Generative AI narrows topics", "doi": "10.1/fake1", "a": "x"},
                         {"t": "Diversity of science", "doi": "10.1/fake2", "a": "y"}]}
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "q.json"
            f.write_text(json.dumps([{"id": "Q1", "query": '"generative AI" AND topics', "purpose": "component"},
                                     {"id": "Q2", "query": "a AND NOT b", "purpose": "component"}]), encoding="utf-8")
            raw, out_dir = Path(d) / "raw", Path(d) / "merged"
            with mock.patch.object(search, "get_json", lambda url, *a, **k: hits), mock.patch.object(search, "RAW_DIR", raw):
                rc, out = run_main(search, ["search.py", "--queries", str(f), "--sources", "fake"])
                _, dry = run_main(search, ["search.py", "--dry-run", "--queries", str(f), "--sources", "fake"])
            self.assertEqual(rc, 0, out)
            self.assertIn("SKIPPED", out)                                    # Q2 有 NOT：该来源不支持，跳过而不是改写
            self.assertIn("fake:            generative AI topics", dry)
            self.assertIn("SKIPPED（NOT is not supported）", dry)
            self.assertEqual(sorted(p.name for p in raw.glob("*.json")), ["fake_Q1.json"])
            with mock.patch.object(merge, "RAW_DIR", raw), mock.patch.object(merge, "OUT_DIR", out_dir):
                self.assertEqual([p.name for p in merge.raw_files("")], ["fake_Q1.json"])
                rc, _ = run_main(merge, ["merge.py"])
            self.assertEqual(rc, 0)
            merged = json.loads((out_dir / "merged.json").read_text(encoding="utf-8"))
        self.assertEqual(merged["meta"]["counts"]["sources"], {"fake": 2})


class TestThreeSourceMerge(unittest.TestCase):
    def test_merge_with_crossref_results(self):
        with tempfile.TemporaryDirectory() as d:
            raw, out_dir = Path(d) / "raw", Path(d) / "merged"
            raw.mkdir()
            for p in (EXAMPLE / "results" / "raw").glob("*_v2.json"):
                shutil.copy(p, raw / p.name)
            for qid, data in replay_crossref(self, FIX / "crossref_queries.json").items():
                (raw / f"crossref_{qid}_v2.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(merge, "RAW_DIR", raw), mock.patch.object(merge, "OUT_DIR", out_dir):
                rc, out = run_main(merge, ["merge.py", "--suffix", "_v2"])
            self.assertEqual(rc, 0, out)
            merged = json.loads((out_dir / "merged_v2.json").read_text(encoding="utf-8"))
        srcs = merged["meta"]["counts"]["sources"]
        self.assertTrue(any("crossref" in k for k in srcs), srcs)
        self.assertEqual(sum(1 for i in merged["meta"]["inputs"] if i["source_api"] == "crossref"), 3)


if __name__ == "__main__":
    unittest.main()
