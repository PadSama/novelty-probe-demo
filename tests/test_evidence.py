#!/usr/bin/env python3
"""证据 JSON（novelty_probe/evidence.py、scripts/evidence.py）的离线测试：导入与还原、渲染、检查、种子、核验写回。不联网。"""
import contextlib
import copy
import io as _io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import CHILD_ENV, EXAMPLE, ROOT, load  # noqa: E402

from novelty_probe import config, evidence, i18n  # noqa: E402
from novelty_probe.io import read_text  # noqa: E402

snowball = load("snowball")
CFG = config.defaults()
TABLES = {"": EXAMPLE / "evidence" / "evidence_table.md", "_v2": EXAMPLE / "evidence" / "evidence_table_v2.md"}


def imported(suffix=""):
    return evidence.import_markdown(read_text(TABLES[suffix]), CFG, source=TABLES[suffix].name)


def example_index(suffix=""):
    return evidence.load_index(EXAMPLE / "results" / "merged" / f"merged{suffix}.json")


class TestImportRender(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("zh")

    def test_round_trip_is_exact(self):
        for suffix, path in TABLES.items():
            with self.subTest(table=path.name):
                text = read_text(path)
                doc = evidence.import_markdown(text, CFG)
                self.assertEqual(evidence.render_markdown(doc), text)
                self.assertEqual(len(doc["rows"]), 10)
                self.assertTrue(all(r["rationale"] for r in doc["rows"]))
                self.assertEqual(doc["meta"]["language"], "zh")
                # JSON 本身也能还原（写盘再读）
                again = json.loads(json.dumps(doc, ensure_ascii=False))
                self.assertEqual(evidence.render_markdown(again), text)

    def test_fields(self):
        r = imported()["rows"][1]
        self.assertEqual((r["rank"], r["merged_id"], r["year"]), (2, "M031", 2023))
        self.assertEqual((r["doi"], r["arxiv_id"]), ("10.1126/sciadv.adn5290", "2312.00506"))
        self.assertEqual(r["labels"], {"research_question": "overlap", "mechanism": "overlap", "context": "differ",
                                       "data_method": "differ", "expected_findings": "overlap"})
        self.assertTrue(r["verified_text"].startswith("Crossref HTTP 200 · 题目一致"))
        self.assertEqual(r["cells_raw"], {})

    def test_english_rendering_changes_only_structure(self):
        doc = imported()
        doc["rows"][0]["verification"] = {"doi": doc["rows"][0]["doi"], "crossref": {"outcome": "found", "http": 200,
                                          "title": "T", "title_match": True}, "openalex": None, "landing": {"outcome": "skipped"}}
        en = evidence.render_markdown(doc, "en")
        zh = evidence.render_markdown(doc, "zh")
        self.assertIn("| rank | Authors | Year | Title | DOI/arXiv | Research question | Mechanism | Context | "
                      "Data and methods | Expected findings | verified |", en)
        self.assertIn("Crossref HTTP 200 · title matches · T; Landing page skipped |", en)
        self.assertIn("Crossref HTTP 200 · 题目一致 · T；落地页 skipped |", zh)
        self.assertIn("## 判定依据", en)                                   # 研究者写的文字不翻译
        self.assertEqual(i18n.get_language(), "zh")                        # 渲染不改变当前界面语言

    def test_markdown_escapes_and_raw_cells(self):
        text = ("# t\n\n| rank | Title | DOI/arXiv | Research question | verified |\n|---|---|---|---|---|\n"
                "| 1 | A \\| B | UNVERIFIED | overlap | x |\n| 2 | C | doi:10.1/x · arXiv:2401.00001 | differ | y \\| z |\n")
        doc = evidence.import_markdown(text, CFG)
        self.assertEqual(doc["meta"]["language"], "en")
        self.assertEqual(doc["rows"][0]["title"], "A | B")
        self.assertEqual(doc["rows"][0]["cells_raw"], {"id": "UNVERIFIED"})
        self.assertEqual(doc["rows"][1]["verified_text"], "y | z")
        self.assertEqual(evidence.render_markdown(doc), text)

    def test_document_written_as_json_renders_and_reimports(self):
        doc = evidence.new_document(CFG, "en")
        doc["rows"] = [{"rank": 1, "merged_id": "M001", "authors": "A; B", "year": 2024, "title": "Paper | one",
                        "doi": "10.1/x", "arxiv_id": None, "labels": {f["key"]: "unknown" for f in CFG["facets"]},
                        "verification": {"doi": None}, "rationale": {"note": "", "lines": ["- all unknown: no abstract", ""]}}]
        md = evidence.render_markdown(doc)
        self.assertTrue(md.startswith("# Evidence table\n\n## Table\n\n| rank | Authors |"))
        self.assertIn("| 1 | A; B | 2024 | Paper \\| one | doi:10.1/x | unknown | unknown | unknown | unknown | unknown | UNVERIFIED |", md)
        self.assertIn("**1 · M001**\n- all unknown: no abstract", md)
        back = evidence.import_markdown(md, CFG)
        self.assertEqual(back["rows"][0]["title"], "Paper | one")
        self.assertEqual(back["rows"][0]["merged_id"], "M001")
        self.assertEqual(evidence.render_markdown(back), md)

    def test_no_table(self):
        with self.assertRaises(evidence.EvidenceError):
            evidence.import_markdown("# nothing\n\n| a | b |\n|---|---|\n", CFG)


class TestCheck(unittest.TestCase):
    def test_example_tables_pass(self):
        for suffix in TABLES:
            with self.subTest(suffix=suffix or "v1"):
                self.assertEqual(evidence.check(imported(suffix), example_index(suffix)), [])

    def test_violations_are_reported(self):
        doc = imported()
        rows = doc["rows"]
        rows[1]["rationale"]["lines"][1] += ' 又见 "writers become collectively more creative"'
        rows[2]["year"] = 2019
        rows[3]["doi"] = "10.9999/made-up"
        rows[4]["labels"]["mechanism"] = "maybe"
        del rows[5]["labels"]["context"]
        rows[6]["title"] = "A different title"
        rows[7]["rank"] = 7
        rows[8]["merged_id"] = "M999"
        findings = evidence.check(doc, example_index())
        text = "\n".join(m for _, m in findings)
        for part in ('"writers become collectively more creative"', "年份 2019", "doi:10.9999/made-up", "'maybe'",
                     "缺少面 context", "题目与检索结果不同", "rank 7 重复", "M999"):
            self.assertIn(part, text)
        levels = {m.split("：")[0]: lvl for lvl, m in findings}
        self.assertEqual(levels["rank 9"], "warning")                       # 判定依据标题与合并结果的编号对不上：提醒

    def test_authors_against_authors_file(self):
        doc = imported()
        people = [{"doi": "10.1126/sciadv.adn5290", "authors": ["Anil Rajnikant Doshi", "Oliver Hauser"]},
                  {"doi": "10.1038/s41586-025-09640-5", "authors": ["Zhen Zhang", "Zhichu Ren", "Chia-Wei Hsu", "D"]}]
        idx = example_index()
        idx.authors = {("doi", evidence.norm_doi(p["doi"])): p for p in people}
        self.assertEqual(evidence.check(doc, idx), [])
        doc["rows"][1]["authors"] = "Anil Doshi; Oliver Hauser"
        self.assertIn("Anil Rajnikant Doshi; Oliver Hauser", evidence.check(doc, idx)[0][1])

    def test_quote_helpers(self):
        self.assertEqual(evidence.quotes_in('- 数据与方法 overlap："Scopus database ... based on 945 research papers"'),
                         ["Scopus database ... based on 945 research papers"])
        self.assertEqual(evidence.quotes_in('- 梳理"生成式 AI 在教育中"这一文献'), [])           # 中文转述不查
        self.assertIsNone(evidence.quotes_in('- odd "quote'))
        abstract = "Data from the Scopus database, based on 945 research papers, were analysed (2010–2016)."
        self.assertTrue(evidence.quote_found("Scopus database ... based on 945 research papers", [abstract]))
        self.assertTrue(evidence.quote_found("DATA FROM the Scopus database", [abstract]))      # 大小写、标点不计
        self.assertFalse(evidence.quote_found("based on 945 papers", [abstract]))
        self.assertFalse(evidence.quote_found("based on 945 research papers ... Data from", [abstract]))   # 省略号两侧须依次出现

    def test_cited_version_abstract(self):
        """本篇没有摘要、判定依据注明了另一个版本的 DOI：那份摘要（在检索结果中）可以作为引文来源。"""
        doc = imported("_v2")
        row = doc["rows"][2]
        self.assertIn("doi:10.48550/arxiv.2412.07727", "".join(row["rationale"]["lines"]))
        self.assertEqual(evidence.check(doc, example_index("_v2")), [])
        stripped = copy.deepcopy(doc)
        r = stripped["rows"][2]
        r["rationale"]["lines"] = [l.replace("doi:10.48550/arxiv.2412.07727", "（来源略）") for l in r["rationale"]["lines"]]
        msgs = [m for _, m in evidence.check(stripped, example_index("_v2"))]
        self.assertTrue(any("找不到这篇的摘要" in m for m in msgs), msgs)

    def test_seeds_from_json_and_markdown(self):
        doc = imported()
        with tempfile.TemporaryDirectory() as d:
            j = Path(d) / "evidence_table.json"
            j.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            from_json = snowball.seeds_from_evidence(j, 2)
            from_md = snowball.seeds_from_evidence(TABLES[""], 2)
        self.assertEqual(from_json, from_md)
        self.assertEqual(from_json, [("rank 2", "10.1126/sciadv.adn5290", "2312.00506"),
                                     ("rank 4", "10.1145/3635636.3656204", "2402.01536")])


class TestEnglishTable(unittest.TestCase):
    """英文证据表全流程：生成英文视图 → 作为 Markdown 重新导入 → 检查 → 取种子 → 核验写回（英文 verified 列）。"""

    def tearDown(self):
        i18n.set_language("zh")

    def test_full_flow(self):
        verify = load("verify")
        en_text = evidence.render_markdown(imported(), "en")
        doc = evidence.import_markdown(en_text, CFG)
        self.assertEqual(doc["meta"]["language"], "en")
        self.assertEqual(evidence.render_markdown(doc), en_text)
        self.assertEqual(evidence.check(doc, example_index()), [])
        with tempfile.TemporaryDirectory() as d:
            md, js = Path(d) / "evidence_table.md", Path(d) / "evidence_table.json"
            md.write_text(en_text, encoding="utf-8")
            self.assertEqual(snowball.seeds_from_evidence(md, 2)[0], ("rank 2", "10.1126/sciadv.adn5290", "2312.00506"))
            doc["meta"]["markdown"] = str(md)
            js.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

            def fake(doi, title, landing):
                v = {"doi": doi, "crossref": {"outcome": "found", "http": 200, "title": title, "title_match": True},
                     "openalex": None, "landing": {"outcome": "skipped"}, "metadata_ok": True}
                return v, {"crossref_res": {"chain": [], "attempts": 1}, "meta": None, "landing_res": None}
            argv = ["verify.py", "--table", str(js), "--no-landing", "--lang", "en"]
            with mock.patch.object(verify, "verify_doi", side_effect=fake), mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stdout(_io.StringIO()):
                self.assertEqual(verify.main(), 0)
            rendered = read_text(md)
        self.assertIn("| Crossref HTTP 200 · title matches · Generative AI enhances individual creativity but reduces the "
                      "collective diversity of novel content; Landing page skipped |", rendered)
        self.assertIn("| rank | Authors | Year | Title | DOI/arXiv | Research question |", rendered)


class TestEvidenceCommand(unittest.TestCase):
    def run_cmd(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "evidence.py"), *map(str, args)], capture_output=True,
                              text=True, encoding="utf-8", env=CHILD_ENV, cwd=cwd)

    def test_import_render_check_and_edit_guard(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PROJECT.md").write_text("marker\n", encoding="utf-8")
            (root / "evidence").mkdir()
            (root / "results" / "merged").mkdir(parents=True)
            md = root / "evidence" / "evidence_table_v2.md"
            md.write_text(read_text(TABLES["_v2"]), encoding="utf-8")
            (root / "results" / "merged" / "merged_v2.json").write_text(
                read_text(EXAMPLE / "results" / "merged" / "merged_v2.json"), encoding="utf-8")
            r = self.run_cmd("import-md", md, "--root", root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("逐字相同", r.stdout)
            js = md.with_suffix(".json")
            doc = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual((doc["meta"]["markdown"], doc["meta"]["results"]),
                             ("evidence/evidence_table_v2.md", "results/merged/merged_v2.json"))
            r = self.run_cmd("check", js, "--root", root)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("检查通过：10 行", r.stdout)
            # 渲染：未改动的 Markdown 可以覆盖；手工改过之后拒绝覆盖
            self.assertEqual(self.run_cmd("render", js, "--root", root).returncode, 0)
            self.assertEqual(read_text(md), read_text(TABLES["_v2"]))
            md.write_text(read_text(md).replace("证据表 v2", "证据表 v2（手改）"), encoding="utf-8")
            r = self.run_cmd("render", js, "--root", root, "--lang", "en")
            self.assertEqual(r.returncode, 2)
            self.assertIn("edited by hand", r.stderr)
            # 另存一份英文视图不受影响
            en = root / "evidence" / "evidence_table_v2.en.md"
            self.assertEqual(self.run_cmd("render", js, "--root", root, "--lang", "en", "--out", en).returncode, 0)
            self.assertIn("| rank | Authors | Year | Title |", read_text(en))
            # check 发现问题时退出码 1
            doc["rows"][0]["labels"]["mechanism"] = "maybe"
            js.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            r = self.run_cmd("check", js, "--root", root, "--lang", "en")
            self.assertEqual(r.returncode, 1)
            self.assertIn("1 problems", r.stdout)


class TestVerifyJson(unittest.TestCase):
    """verify.py --table <json>：结构化结果写进 rows[].verification，Markdown 由 JSON 重新生成；手工改过的 Markdown 不覆盖。"""

    def test_verify_writes_structured_results(self):
        verify = load("verify")
        text = ("# t\n\n| rank | 题目 | DOI/arXiv | 研究问题 | verified |\n|---|---|---|---|---|\n"
                "| 1 | DataCite Paper | doi:10.0000/datacite | overlap | 待核验 |\n| 2 | Only arXiv | arXiv:2401.00001 | differ | 待核验 |\n")
        result = {"doi": "10.0000/datacite", "crossref": {"outcome": "not_registered", "agency": "datacite"},
                  "openalex": {"outcome": "found", "title": "DataCite Paper", "title_match": True},
                  "landing": {"outcome": "skipped"}, "metadata_ok": True}
        fake = lambda doi, title, landing: (dict(result), {"crossref_res": {"chain": [], "attempts": 0},  # noqa: E731
                                                            "meta": None, "landing_res": None})
        with tempfile.TemporaryDirectory() as d:
            md, js = Path(d) / "evidence_table.md", Path(d) / "evidence_table.json"
            md.write_text(text, encoding="utf-8")
            doc = evidence.import_markdown(text, CFG)
            doc["meta"]["markdown"] = str(md)
            js.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            argv = ["verify.py", "--table", str(js), "--no-landing"]
            with mock.patch.object(verify, "verify_doi", side_effect=fake), mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stdout(_io.StringIO()):
                self.assertEqual(verify.main(), 0)
            out = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(out["rows"][0]["verification"]["crossref"]["agency"], "datacite")
            self.assertIn("checked_at", out["rows"][0]["verification"])
            self.assertEqual(out["rows"][1]["verification"]["doi"], None)
            self.assertNotIn("verified_text", out["rows"][0])
            rendered = read_text(md)
            self.assertIn("| Crossref 无记录（Datacite 登记的 DOI）；OpenAlex · 题目一致 · DataCite Paper；落地页 skipped |", rendered)
            self.assertIn("| UNVERIFIED |", rendered)
            # 手工改过 Markdown 之后再核验：JSON 照常更新，Markdown 不覆盖
            md.write_text(rendered.replace("# t", "# t (edited)"), encoding="utf-8")
            err = _io.StringIO()
            with mock.patch.object(verify, "verify_doi", side_effect=fake), mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(err):
                self.assertEqual(verify.main(), 0)
            self.assertIn("手工改过", err.getvalue())
            self.assertTrue(read_text(md).startswith("# t (edited)"))
            # 重新导入改过的 Markdown：沿用 JSON 里的结构化核验结果
            again = evidence.import_markdown(read_text(md), CFG)
            self.assertEqual(evidence.keep_structured_verification(again, json.loads(js.read_text(encoding="utf-8"))), 1)
            self.assertIn("verification", again["rows"][0])


if __name__ == "__main__":
    unittest.main()
