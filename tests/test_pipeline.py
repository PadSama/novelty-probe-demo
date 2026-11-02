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

textmatch, qa, enrich, search, snowball, merge, compare = (load("textmatch"), load("qa"), load("enrich"),
                                                           load("search"), load("snowball"), load("merge"),
                                                           load("compare"))
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
        for bad in ['NOT a AND b', 'a NOT b', '(a OR NOT b) AND c', 'a AND NOT NOT b', 'a AND NOT', '(a OR b) NOT c',
                    'a AND not b', '(a or b) AND c', 'a AND -b', '!a AND b']:   # 小写运算符、减号都会被 API 误解
            with self.subTest(query=bad), self.assertRaises(ValueError):
                search.parse_query(bad)

    def test_not_translation(self):
        q = '("generative AI" OR ChatGPT) AND narrowing AND NOT ("narrow AI" OR narrow-AI)'
        self.assertEqual(search.to_openalex(q), q)                      # OpenAlex 原生支持大写 NOT，照原样发送
        self.assertEqual(search.to_s2_bulk(q), '("generative AI" | ChatGPT) + narrowing + -("narrow AI" | "narrow AI")')
        self.assertEqual(search.to_s2_bulk("a AND NOT b"), "a + -b")

    def test_openalex_result_without_not_in_oql_is_rejected(self):
        q = {"id": "Q1", "query": "narrowing AND NOT (\"narrow AI\")", "purpose": "component"}
        good = {"meta": {"count": 1, "x_query": {"oql": "(narrowing NOT stemmed \"narrow AI\")"}}, "results": []}
        bad = {"meta": {"count": 1, "x_query": {"oql": "(stemmed \"narrow AI\" AND narrowing)"}}, "results": []}
        with mock.patch.object(search, "get_json", return_value=good), mock.patch("time.sleep"):
            self.assertEqual(search.search_openalex(q, None)[0]["total_hits"], 1)
        with mock.patch.object(search, "get_json", return_value=bad), mock.patch("time.sleep"), \
                self.assertRaisesRegex(RuntimeError, "NOT"):
            search.search_openalex(q, None)


# ---------- S2 本地重排 ----------

class TestS2LocalRank(unittest.TestCase):
    Q = '("generative AI" OR ChatGPT) AND (narrowing OR "topic diversity")'

    def paper(self, title, abstract=None, cites=0, doi=None):
        return {"title": title, "abstract": abstract, "citationCount": cites, "year": 2024,
                "externalIds": {"DOI": doi} if doi else {}, "venue": "V"}

    def test_order_and_abstract_strata(self):
        papers = [self.paper("Old famous survey", "generative AI overview", cites=9000),              # 只满足 1 组
                  self.paper("ChatGPT narrows topics", "ChatGPT narrowing topic diversity narrowing", cites=1),
                  self.paper("Generative AI and narrowing", "generative AI in science", cites=50),
                  self.paper("ChatGPT and topic diversity"),                                         # 无摘要
                  self.paper("Unrelated title")]                                                    # 无摘要
        ranked = search.s2_local_rank(papers, self.Q, top_n=5)
        order = [i for i, _ in ranked]
        self.assertEqual(order.index(1) < order.index(0), True)          # 满足两组的排在高被引的综述前面
        self.assertEqual(sorted(order), [0, 1, 2, 3, 4])
        self.assertEqual(order[0], 1)                                     # 有摘要的第一名排第一
        self.assertIn(3, order[:3])                                       # 标题命中两组的无摘要记录按比例穿插，不沉底
        self.assertEqual(order[-1], 4)                                    # 标题一组都不命中的无摘要记录排最后
        info = dict(ranked)[1]
        self.assertEqual((info["groups_matched"], info["has_abstract"]), (2, True))

    def test_same_title_kept_once(self):
        papers = [self.paper("Call for papers on generative AI narrowing", "generative AI narrowing", doi=f"10.1/{i}")
                  for i in range(4)] + [self.paper("ChatGPT narrows topics", "ChatGPT narrowing topic diversity")]
        ranked = search.s2_local_rank(papers, self.Q, top_n=5)
        self.assertEqual(len(ranked), 2)                                   # 四条同题启事只留一条
        self.assertEqual(sum(info.get("same_title_dropped", 0) for _, info in ranked), 3)

    def test_pagination_and_cap(self):
        pages = {None: {"total": 5, "token": "t2", "data": [self.paper(f"ChatGPT narrowing {i}", "ChatGPT narrowing")
                                                           for i in range(3)]},
                 "t2": {"total": 5, "token": None, "data": [self.paper(f"Generative AI topic diversity {i}", "generative AI")
                                                            for i in range(2)]}}
        urls = []

        def fake(url, headers=None, retries=5):
            urls.append(url)
            token = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("token", [None])[0]
            return pages[token]

        q = {"id": "Q1", "query": self.Q, "purpose": "component"}
        with mock.patch.object(search, "get_json", fake), mock.patch("time.sleep"):
            meta, records = search.search_s2(q, None)
        self.assertEqual(len(urls), 2)
        self.assertEqual((meta["pool"]["retrieved"], meta["pool"]["truncated"], meta["total_hits"]), (5, False, 5))
        self.assertEqual(len(records), 5)
        self.assertTrue(all("local_rank" in r for r in records))
        with mock.patch.object(search, "get_json", fake), mock.patch.object(search, "S2_MAX_RECORDS", 3), \
                mock.patch("time.sleep"):
            meta, records = search.search_s2(q, None)
        self.assertEqual((meta["pool"]["retrieved"], meta["pool"]["truncated"]), (3, True))


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
        recs = json.loads((out / "chase_C1_t.json").read_text(encoding="utf-8"))["records"]
        got = {r["chase"]["openalex_id"]: (r["chase"]["links"], r["chase"]["directions"]) for r in recs}
        self.assertEqual(got, {"W10": (2, ["backward"]), "W20": (2, ["forward"]),
                               "W11": (1, ["backward"]), "W21": (1, ["forward"])})   # 种子的预印本版 W22 被去掉
        keys = [(-r["chase"]["links"], -r["chase"]["similarity"]) for r in recs]
        self.assertEqual(keys, sorted(keys))                                            # links 降序，同 links 按相似度
        with (out / "chase_C1_t.csv").open(encoding="utf-8-sig") as f:
            rows = {r["openalex_id"]: r for r in csv.DictReader(f)}
        self.assertEqual(rows["W21"]["in_search"], "M007")                              # 已在检索结果中
        self.assertEqual(sum("cursor=c2" in p for p in self.paths), 2)                  # 每个种子都翻了页


class TestSnowballCocite(unittest.TestCase):
    def setUp(self):
        def work(wid, title, refs=(), cited=5, doi=None):
            return {"id": f"https://openalex.org/{wid}", "doi": f"https://doi.org/{doi or '10.1/' + wid.lower()}",
                    "title": title, "display_name": title, "publication_year": 2025, "type": "article",
                    "primary_location": None, "locations": [], "abstract_inverted_index": None, "cited_by_count": cited,
                    "referenced_works": [f"https://openalex.org/{r}" for r in refs]}

        seeds = {"10.1/seed1": work("W1", "Generative AI reduces collective diversity of stories"),
                 "10.1/seed2": work("W2", "LLMs homogenize creative ideas across users")}
        citers = [work("C1", "Scientists and AI tools in the lab", ["W1", "W50", "W51"]),
                  work("C2", "Scientists adopting large language models", ["W2", "W50", "W51"]),
                  work("C3", "Re: Something about scientists", ["W1", "W50"]),        # 来信：不计
                  work("C4", "Scientists' topic choice with AI", ["W1", "W50", "W53", "W52"]),
                  work("C5", "Scientists and AI tools in the lab", ["W1", "W51"], doi="10.2139/ssrn.5")]  # C1 的另一版本
        cocited = {"W50": work("W50", "A generic reporting guideline for reviews", cited=10000),
                   "W51": work("W51", "AI narrows the focus of modern science", cited=4),
                   "W53": work("W53", "AI narrows the focus of modern science", cited=0, doi="10.48550/arxiv.1"),  # W51 的预印本
                   "W52": work("W52", "Only one citer cites me")}
        self.filters = []

        def handle(h):
            url = urllib.parse.urlsplit(h.path)
            q = dict(urllib.parse.parse_qsl(url.query))
            if url.path.startswith("/works/doi:"):
                found = seeds.get(urllib.parse.unquote(url.path[len("/works/doi:"):]).lower())
                return reply(h, 200 if found else 404, json.dumps(found or {}), "application/json")
            flt = q.get("filter", "")
            self.filters.append(flt)
            if flt.startswith("cites:") and q.get("per-page") == "1":
                return reply(h, 200, json.dumps({"meta": {"count": 25}, "results": []}), "application/json")
            if flt.startswith("cites:"):
                return reply(h, 200, json.dumps({"meta": {"next_cursor": None}, "results": citers}), "application/json")
            if flt.startswith("openalex_id:"):
                ids = flt[len("openalex_id:"):].split("|")
                return reply(h, 200, json.dumps({"results": [cocited[i] for i in ids if i in cocited]}), "application/json")
            reply(h, 400, "{}", "application/json")

        self.server = MockServer(handle)
        self.tmp = tempfile.TemporaryDirectory()
        out = Path(self.tmp.name)
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

    def test_cocitation_through_filtered_citers(self):
        argv = ["snowball.py", "--seeds", "10.1/seed1,10.1/seed2", "--suffix", "_t", "--cocite",
                "--citer-filter", "scientist*"]
        with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout"):
            self.assertEqual(snowball.main(), 0)
        data = json.loads((Path(self.tmp.name) / "chase_C2_t.json").read_text(encoding="utf-8"))
        rows = [(r["chase"]["path"], r["chase"]["openalex_id"], r["chase"].get("support")) for r in data["records"]]
        # W51 与其预印本 W53 合并计数（C1 组、C2、C4）；C1 与 C5 是同一研究的两个版本，只算一篇
        self.assertEqual([x for x in rows if x[0] == "cocited"], [("cocited", "W51", 3), ("cocited", "W50", 3)])
        self.assertEqual(sorted(x[1] for x in rows if x[0] == "citer"), ["C1", "C2", "C4"])    # 来信 C3 不计
        m = data["meta"]
        self.assertEqual((m["citing_total_unfiltered"], m["citing_filtered"], m["citers_used"], m["citer_versions_merged"],
                          m["cocited_kept"]), (25, 5, 3, 1, 2))
        self.assertEqual(m["citing_notices_excluded"], ["Re: Something about scientists"])
        self.assertTrue(any(f.endswith(",title_and_abstract.search:scientists") for f in self.filters))
        w51 = next(r for r in data["records"] if r["chase"]["openalex_id"] == "W51")
        self.assertEqual((w51["chase"]["via"], w51["chase"]["versions"], w51["chase"]["norm_support"]),
                         (["C1", "C2", "C4"], ["W53"], 1.5))                      # 支持数相同，按支持数/√被引次数


# ---------- 合并：版本识别、年份、RRF ----------

class TestMergeRanked(unittest.TestCase):
    NATURE = "Artificial intelligence tools expand scientists’ impact but contract science’s focus"

    def run_merge(self, files):
        with tempfile.TemporaryDirectory() as d:
            raw, out = Path(d) / "raw", Path(d) / "out"
            raw.mkdir()
            for name, (query, records) in files.items():
                src, qid = name.split("_")
                meta = {"source_api": src, "query_id": qid, "query_original": query, "conversion": f"c-{src}",
                        "sort": "s", "total_hits": len(records), "returned": len(records), "retrieved_at": "t"}
                recs = [{"title": t, "year": y, "doi": doi, "arxiv_id": ax, "venue": v, "abstract": ab,
                         "source_api": src, "query_id": qid} for t, y, doi, ax, v, ab in records]
                (raw / f"{name}_t.json").write_text(json.dumps({"meta": meta, "records": recs}), encoding="utf-8")
            with mock.patch.object(merge, "RAW_DIR", raw), mock.patch.object(merge, "OUT_DIR", out), \
                    mock.patch.object(sys, "argv", ["merge.py", "--suffix", "_t"]), mock.patch("sys.stdout"):
                self.assertEqual(merge.main(), 0)
            data = json.loads((out / "merged_t.json").read_text(encoding="utf-8"))
            with (out / "candidates_t.csv").open(encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        return data, rows

    def test_versions_years_and_review(self):
        q = '("AI tools" OR "artificial intelligence") AND (narrowing OR focus)'
        data, rows = self.run_merge({
            "openalex_Q1": (q, [
                (self.NATURE, 2026, "10.1038/s41586-025-09922-y", None, "Nature", None),
                ("Re: " + self.NATURE, 2026, "10.1016/j.eururo.2026.04.004", None, "Eur Urol", None),
                (self.NATURE.replace("’", "'") + " (Just accepted by Nature, to be online soon)", 2024,
                 "10.48550/arxiv.2412.07727", "2412.07727", "arXiv", "AI adoption shrinks the collective volume of topics"),
                ("Identifying disruptive technologies via hypergraph models and language models", 2026,
                 "10.21227/1051-8s48", None, "IEEE DataPort", None),
                ("Identifying disruptive technologies via hypergraph models and language models", 2026,
                 "10.36227/techrxiv.177223104.47525491/v1", None, None, None),
                ("A study of focus in artificial intelligence research groups", 2002,
                 "10.1109/hicss.1993.270676/full/html?utm_source=x", None, "HICSS", "AI tools narrowing focus"),
            ]),
            "semanticscholar_Q1": (q, [
                (self.NATURE, 2026, "10.1038/s41586-025-09922-y", None, "Nature", None),
                ("A study of focus in artificial intelligence research groups", 1993, "10.1109/HICSS.1993.270676",
                 None, "HICSS", None),
            ]),
        })
        recs = {x["merged_id"]: x for x in data["records"]}
        hao = next(x for x in recs.values() if x["doi"] == "10.1038/s41586-025-09922-y")
        self.assertEqual((hao["arxiv_id"], hao["year"], hao["year_first"], hao["title_linked"]),
                         ("2412.07727", 2026, 2024, True))                       # 预印本并入；年份取正式发表
        self.assertTrue(hao["abstract"])                                         # 摘要来自预印本
        letter = next(x for x in recs.values() if x["doi"] == "10.1016/j.eururo.2026.04.004")
        self.assertIsNot(letter, hao)                                            # "Re:" 来信不合并
        hicss = next(x for x in recs.values() if x["doi"] and "hicss" in x["doi"].lower())
        self.assertEqual((hicss["year"], len(hicss["raw_refs"])), (1993, 2))     # DOI 去掉 /full/html?… 后合并
        self.assertEqual(hicss["doi"], "10.1109/hicss.1993.270676")
        reviews = data["meta"]["review_pairs"]
        self.assertEqual(len(reviews), 1)                                        # 数据集 DOI：只标出，不合并
        self.assertIn("data-repository", reviews[0]["reason"])
        flagged = [x for x in recs.values() if x["review"]]
        self.assertEqual(sorted(x["doi"].split("/")[0] for x in flagged), ["10.21227", "10.36227"])  # 两条都注明
        self.assertEqual(rows[0]["merged_id"], hao["merged_id"])                 # 两个列表都排第 1，RRF 最高

    def test_rrf_then_bm25(self):
        q = '("generative AI") AND (narrowing OR "topic diversity")'
        data, rows = self.run_merge({
            "openalex_Q1": (q, [("Generative AI and narrowing of topics", 2025, "10.1/a", None, "J", "generative AI narrowing"),
                                ("Generative AI in classrooms today", 2025, "10.1/b", None, "J", "generative AI narrowing"),
                                ("Generative AI narrowing topic diversity again", 2025, "10.1/c", None, "J",
                                 "generative AI narrowing narrowing topic diversity")]),
            "semanticscholar_Q1": (q, [("Generative AI in classrooms today", 2025, "10.1/b", None, "J", None),
                                       ("Generative AI and narrowing of topics", 2025, "10.1/a", None, "J", None),
                                       ("Unrelated paper about soils and wetlands", 2025, "10.1/d", None, "J", "soil")]),
        })
        self.assertEqual([r["doi"] for r in rows], ["10.1/a", "10.1/b", "10.1/c", "10.1/d"])
        self.assertEqual(float(rows[0]["rrf"]), float(rows[1]["rrf"]))           # a、b 名次互换，RRF 相同
        self.assertGreater(float(rows[0]["bm25"]), float(rows[1]["bm25"]))       # 由 BM25 决定先后
        self.assertEqual(list(rows[0])[:5], ["rank", "merged_id", "rrf", "bm25", "n_conform"])


# ---------- 比较几轮结果 ----------

class TestCompare(unittest.TestCase):
    def test_known_item_and_noise(self):
        q = '("generative AI") AND narrowing'
        recs = [{"merged_id": "M001", "title": "Generative AI and narrow AI systems", "abstract": "narrow AI", "year": 2024,
                 "doi": "10.1/noise", "arxiv_id": None, "alt_ids": [], "rrf": 0.03, "bm25": 2.0},
                {"merged_id": "M002", "title": "Generative AI narrowing science", "abstract": "x", "year": 2026,
                 "doi": "10.1038/s41586-025-09922-y", "arxiv_id": "2412.07727", "alt_ids": [], "rrf": 0.02, "bm25": 1.0}]
        with tempfile.TemporaryDirectory() as d:
            out, raw = Path(d) / "out", Path(d) / "raw"
            out.mkdir()
            raw.mkdir()
            (out / "merged_t.json").write_text(json.dumps({"meta": {"method": "x", "candidates": {
                "works_tied_with_cutoff": 1}}, "records": recs}), encoding="utf-8")
            (raw / "openalex_Q1_t.json").write_text(json.dumps({"meta": {"query_id": "Q1", "query_original": q},
                                                                "records": []}), encoding="utf-8")
            (out / "chase_C2_t.csv").write_text("path,rank,doi,arxiv_id\ncocited,1,10.1038/S41586-025-09922-Y,\n",
                                                encoding="utf-8")
            argv = ["compare.py", "--runs", "_t", "--known", "arXiv:2412.07727", "--ignore-phrases", '"narrow AI"',
                    "--out", str(Path(d) / "r.json")]
            with mock.patch.object(compare, "OUT_DIR", out), mock.patch.object(compare.merge, "RAW_DIR", raw), \
                    mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout"):
                self.assertEqual(compare.main(), 0)
            r = json.loads((Path(d) / "r.json").read_text(encoding="utf-8"))["_t"]
        self.assertEqual(r["known"]["arxiv:2412.07727"], {"rank": 2, "in_top": True, "chase": ["C2/cocited #1"]})
        self.assertEqual((r["top10"]["conform"], r["top10"]["noise"], r["top10"]["genai"]), (1, 1, 2))


if __name__ == "__main__":
    unittest.main()
