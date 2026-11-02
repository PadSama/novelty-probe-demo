#!/usr/bin/env python3
"""novelty-probe 离线自检（第二部分）：文本匹配、检索质量检查、NOT 解析、版本补全。不联网。

运行：python3 -m unittest discover -s tests -v
"""
import csv
import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import ROOT, MockServer, load, reply  # noqa: E402  共用 test_offline 的工具

textmatch, qa, enrich, search, snowball = (load("textmatch"), load("qa"), load("enrich"), load("search"),
                                           load("snowball"))
Doc = textmatch.Doc


# ---------- Porter 词干还原 ----------

class TestPorter(unittest.TestCase):
    def test_matches_snowball_porter_fixture(self):
        pairs = json.loads((ROOT / "tests" / "fixtures" / "porter_pairs.json").read_text(encoding="utf-8"))["pairs"]
        wrong = {w: (textmatch.porter_stem(w), s) for w, s in pairs.items() if textmatch.porter_stem(w) != s}
        self.assertEqual(wrong, {})

    def test_classic_examples(self):
        for word, stem in [("caresses", "caress"), ("ponies", "poni"), ("relational", "relat"), ("as", "a"),
                           ("homogenization", "homogen"), ("homogenizing", "homogen"), ("narrowing", "narrow"),
                           ("scientists", "scientist"), ("diversity", "divers"), ("hopping", "hop"), ("filing", "file")]:
            with self.subTest(word=word):
                self.assertEqual(textmatch.porter_stem(word), stem)


# ---------- 检索词匹配 ----------

class TestTextMatch(unittest.TestCase):
    def test_tokenize_strips_markup(self):
        self.assertEqual(textmatch.tokenize("<i>Large</i> language&nbsp;models’ use"),
                         ["large", "language", "models", "use"])

    def test_phrase_prefix_and_ignore(self):
        doc = Doc("A large language model narrows topics", "Narrow AI systems and homogenizing effects")
        self.assertTrue(textmatch.term_in('"large language models"', doc))     # 按词干匹配短语
        self.assertTrue(textmatch.term_in("homogeniz*", doc))                  # 截断词按前缀匹配
        self.assertFalse(textmatch.term_in('"language large"', doc))           # 短语要求词序
        self.assertTrue(textmatch.term_in("narrowing", doc))                   # narrows 与 narrowing 同词干
        only_ai = Doc("Narrow AI systems are everywhere")
        self.assertFalse(textmatch.term_in("narrowing", only_ai, ignore=['"narrow AI"']))   # 只出现在 "narrow AI" 中
        self.assertTrue(textmatch.term_in("narrowing", doc, ignore=['"narrow AI"']))         # 别处还有 narrows

    def test_query_match_with_not(self):
        include = [['"generative AI"', "ChatGPT"], ["narrowing", '"topic diversity"']]
        exclude = [['"narrow AI"']]
        self.assertTrue(textmatch.query_match(include, Doc("ChatGPT and the narrowing of topics"), exclude))
        self.assertFalse(textmatch.query_match(include, Doc("ChatGPT is a narrow AI"), exclude))   # 命中排除组
        self.assertFalse(textmatch.query_match(include, Doc("Generative AI in classrooms"), exclude))
        self.assertEqual(textmatch.groups_matched(include, Doc("Generative AI in classrooms")), 1)

    def test_bm25_orders_by_term_evidence(self):
        docs = [Doc("generative AI narrows research topics; topic diversity falls"),
                Doc("generative AI in marketing"), Doc("soil chemistry of wetlands")]
        bm = textmatch.BM25(docs, ['"generative AI"', "narrowing", '"topic diversity"'])
        scores = [bm.score(i) for i in range(3)]
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[1], 0)
        self.assertEqual(scores[2], 0)

    def test_version_titles(self):
        nature = "Artificial intelligence tools expand scientists’ impact but contract science’s focus"
        preprint = ("Artificial Intelligence Tools Expand Scientists' Impact but Contract Science's Focus "
                    "(Just accepted by Nature, to be online soon)")
        self.assertTrue(textmatch.version_title_match(nature, preprint))
        self.assertFalse(textmatch.version_title_match(nature, "Re: " + nature))          # 读者来信不是同一研究
        self.assertFalse(textmatch.version_title_match(nature, "Author Correction: " + nature))
        self.assertFalse(textmatch.version_title_match("AI and science", "AI and Science"))  # 太短，不比
        self.assertEqual(textmatch.title_search_words(preprint),
                         ["artificial", "intelligence", "tools", "expand", "scientists", "impact", "but",
                          "contract", "science", "focus"])                                  # 去掉所有格 s 与括注


# ---------- NOT 解析 ----------

class TestParseQuery(unittest.TestCase):
    def test_include_and_exclude_groups(self):
        q = '("generative AI" OR ChatGPT) AND narrowing AND NOT ("narrow AI" OR "narrow artificial intelligence")'
        self.assertEqual(search.parse_query(q),
                         ([['"generative AI"', "ChatGPT"], ["narrowing"]],
                          [['"narrow AI"', '"narrow artificial intelligence"']]))
        self.assertEqual(search.and_groups(q), [['"generative AI"', "ChatGPT"], ["narrowing"]])

    def test_not_syntax_errors(self):
        for bad in ['NOT a AND b', 'a NOT b', '(a OR NOT b) AND c', 'a AND NOT NOT b', 'a AND NOT', '(a OR b) NOT c']:
            with self.subTest(query=bad), self.assertRaises(ValueError):
                search.parse_query(bad)


# ---------- 检索质量检查 ----------

class TestQA(unittest.TestCase):
    def test_check_file_counts_conforming_records(self):
        records = [{"title": "Generative AI narrows research topics", "abstract": None},            # 只靠标题，满足
                   {"title": "A study", "abstract": "We show ChatGPT reduces topic diversity."},      # 靠摘要满足
                   {"title": "Narrow AI in hospitals", "abstract": "ChatGPT is a narrow AI tool."},  # 命中 NOT 组
                   {"title": "Soil chemistry", "abstract": "Wetland soils."}]                        # 不满足
        q = '("generative AI" OR ChatGPT) AND (narrowing OR "topic diversity") AND NOT ("narrow AI")'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "openalex_Q1.json"
            p.write_text(json.dumps({"meta": {"query_original": q}, "records": records}), encoding="utf-8")
            r = qa.check_file(p)
        self.assertEqual((r["records"], r["with_abstract"], r["conform"], r["conform_with_abstract"]), (4, 3, 2, 1))

    def test_reproduces_documented_totals(self):
        """与 RUN_LOG 里记录的质量检查结果一致（v1：177/217，有摘要者 169/178；v2：181/235，170/170）。"""
        for suffix, expected in (("", (177, 217, 169, 178)), ("_v2", (181, 235, 170, 170))):
            with self.subTest(suffix=suffix or "v1"):
                rows = [qa.check_file(p) for p in qa.merge.raw_files(suffix)]
                got = tuple(sum(r[k] for r in rows) for k in ("conform", "records", "conform_with_abstract", "with_abstract"))
                self.assertEqual(got, expected)


# ---------- 从其他版本补摘要 ----------

class TestEnrich(unittest.TestCase):
    TITLE = "Artificial intelligence tools expand scientists’ impact but contract science’s focus"

    def setUp(self):
        def work(wid, doi, title, year, typ, authors, abstract=None):
            return {"id": wid, "doi": f"https://doi.org/{doi}" if doi else None, "display_name": title,
                    "publication_year": year, "type": typ,
                    "abstract_inverted_index": {w: [i] for i, w in enumerate(abstract.split())} if abstract else None,
                    "authorships": [{"author": {"display_name": a}} for a in authors]}

        results = [
            work("W1", "10.1038/s41586-025-09922-y", self.TITLE, 2026, "article", ["Qianyue Hao", "Fengli Xu"]),
            work("W2", "10.1016/j.eururo.2026.04.004", "Re: " + self.TITLE, 2026, "letter", ["Someone Else"]),
            work("W3", "10.48550/arxiv.2412.07727", self.TITLE.replace("’", "'") + " (Just accepted by Nature)",
                 2024, "preprint", ["Qianyue Hao", "Fengli Xu"], "AI adoption shrinks the collective volume of topics"),
            work("W4", "10.9999/same-title-other-team", self.TITLE, 2025, "article", ["Ana Ruiz"], "Other abstract"),
            work("W5", "10.9999/same-title-old", self.TITLE, 2015, "article", ["Qianyue Hao"], "Old abstract"),
        ]
        self.queries = []

        def handle(h):
            self.queries.append(h.path)
            reply(h, 200, json.dumps({"meta": {"count": len(results)}, "results": results}), "application/json")

        self.server = MockServer(handle)
        self.patch = mock.patch.object(enrich, "OPENALEX_URL", self.server.url + "/works")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.server.close()

    def test_adds_abstract_and_arxiv_id_from_preprint(self):
        with tempfile.TemporaryDirectory() as d:
            cand, out = Path(d) / "c.csv", Path(d) / "e.json"
            with cand.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["rank", "merged_id", "title", "year", "doi", "arxiv_id", "abstract"])
                w.writeheader()
                w.writerow({"rank": 1, "merged_id": "M003", "title": self.TITLE, "year": 2026,
                            "doi": "10.1038/s41586-025-09922-y", "arxiv_id": "", "abstract": ""})
                w.writerow({"rank": 2, "merged_id": "M004", "title": "Has everything", "year": 2024,
                            "doi": "10.1/x", "arxiv_id": "2401.00001", "abstract": "Present."})
            with mock.patch.object(sys, "argv", ["enrich.py", "--candidates", str(cand), "--out", str(out)]), \
                    mock.patch("sys.stdout"):
                self.assertEqual(enrich.main(), 0)
            data = json.loads(out.read_text(encoding="utf-8"))
        rec = data["records"][0]
        self.assertEqual([v["doi"] for v in rec["versions"]], ["10.48550/arxiv.2412.07727"])   # 排除来信、他人、年份过远
        self.assertEqual(rec["abstract"], "AI adoption shrinks the collective volume of topics")
        self.assertEqual(rec["abstract_source"]["doi"], "10.48550/arxiv.2412.07727")
        self.assertEqual(rec["arxiv_id_from_version"], "2412.07727")
        self.assertEqual(data["records"][1]["versions"], [])                                    # 不缺信息的不查
        self.assertEqual(len(self.queries), 1)
        self.assertIn("title.search%3Aartificial+intelligence+tools", self.queries[0])
        self.assertEqual(data["meta"]["counts"]["abstract_added"], 1)


# ---------- 引文追踪 ----------

class TestSnowball(unittest.TestCase):
    def setUp(self):
        def work(wid, title, abstract=None, refs=None, doi=None):
            return {"id": f"https://openalex.org/{wid}", "doi": f"https://doi.org/{doi}" if doi else None,
                    "title": title, "display_name": title, "publication_year": 2025, "type": "article",
                    "primary_location": {"source": {"display_name": "J"}}, "locations": [],
                    "abstract_inverted_index": {w: [i] for i, w in enumerate(abstract.split())} if abstract else None,
                    "referenced_works": [f"https://openalex.org/{r}" for r in refs or []], "cited_by_count": 3}

        seed1 = work("W1", "Generative AI reduces collective diversity of stories", "AI ideas make stories similar",
                     ["W10", "W11"], "10.1/seed1")
        seed2 = work("W2", "LLMs homogenize creative ideas across users", "users ideas converge with LLM help",
                     ["W10"], "10.1/seed2")
        works = {
            "W10": work("W10", "Collective diversity and social influence", "diversity of ideas declines", doi="10.1/w10"),
            "W11": work("W11", "Soil chemistry of wetlands", "wetland soils", doi="10.1/w11"),
            "W20": work("W20", "AI tools contract the collective diversity of science", "AI narrows topics", doi="10.1/w20"),
            "W21": work("W21", "Generative AI and stories in classrooms", "stories with AI ideas", doi="10.1/w21"),
            "W22": work("W22", "Generative AI reduces collective diversity of stories (preprint version)", "x",
                        doi="10.48550/arxiv.2401.00009"),
        }
        citing = {"W1": ["W20", "W21", "W22"], "W2": ["W20"]}
        self.paths = []

        def handle(h):
            self.paths.append(h.path)
            url = urllib.parse.urlsplit(h.path)
            q = dict(urllib.parse.parse_qsl(url.query))
            if url.path.startswith("/works/doi:"):
                doi = urllib.parse.unquote(url.path[len("/works/doi:"):]).lower()
                found = {"10.1/seed1": seed1, "10.48550/arxiv.2401.00001": seed1, "10.1/seed2": seed2}.get(doi)
                return reply(h, 200 if found else 404, json.dumps(found or {"error": "nf"}), "application/json")
            flt = q.get("filter", "")
            if flt.startswith("cites:"):
                ids = [w for s in flt[6:].split("|") for w in citing.get(s, [])]
                page = [works[w] for w in ids]
                if q.get("cursor") == "*":            # 第一页只给一条，测试翻页
                    body = {"meta": {"next_cursor": "c2"}, "results": page[:1]}
                else:
                    body = {"meta": {"next_cursor": None}, "results": page[1:]}
                return reply(h, 200, json.dumps(body), "application/json")
            if flt.startswith("openalex_id:"):
                ids = flt[len("openalex_id:"):].split("|")
                return reply(h, 200, json.dumps({"results": [works[w] for w in ids if w in works]}), "application/json")
            reply(h, 400, "{}", "application/json")

        self.server = MockServer(handle)
        self.tmp = tempfile.TemporaryDirectory()
        out = Path(self.tmp.name)
        (out / "merged_t.json").write_text(json.dumps({"records": [
            {"merged_id": "M007", "doi": "10.1/w21", "arxiv_id": None, "alt_ids": [], "title": "x"}]}), encoding="utf-8")
        self.patches = [mock.patch.object(snowball, "OPENALEX_URL", self.server.url + "/works"),
                        mock.patch.object(snowball, "RAW_DIR", out), mock.patch.object(snowball, "OUT_DIR", out),
                        mock.patch.object(snowball, "PAUSE", 0)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.server.close()
        self.tmp.cleanup()

    def test_backward_and_forward_links(self):
        argv = ["snowball.py", "--seeds", "10.1/seed1,10.1/seed2", "--suffix", "_t", "--top", "10"]
        with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout"):
            self.assertEqual(snowball.main(), 0)
        out = Path(self.tmp.name)
        recs = json.loads((out / "openalex_C1_t.json").read_text(encoding="utf-8"))["records"]
        got = {r["chase"]["openalex_id"]: (r["chase"]["links"], r["chase"]["directions"]) for r in recs}
        self.assertEqual(got, {"W10": (2, ["backward"]), "W20": (2, ["forward"]),
                               "W11": (1, ["backward"]), "W21": (1, ["forward"])})   # 种子的预印本版 W22 被去掉
        keys = [(-r["chase"]["links"], -r["chase"]["similarity"]) for r in recs]
        self.assertEqual(keys, sorted(keys))                                            # links 降序，同 links 按相似度
        with (out / "chase_t.csv").open(encoding="utf-8-sig") as f:
            rows = {r["openalex_id"]: r for r in csv.DictReader(f)}
        self.assertEqual(rows["W21"]["in_search"], "M007")                              # 已在检索结果中
        self.assertEqual(sum("cursor=c2" in p for p in self.paths), 2)                  # 每个种子都翻了页


if __name__ == "__main__":
    unittest.main()
