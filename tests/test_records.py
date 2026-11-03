#!/usr/bin/env python3
"""阶段 4：记录带作者与出处、自动可追溯的去重、RIS、运行清单与检索报告、本地匹配的偏差。不联网。"""
import contextlib
import hashlib
import io
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import CHILD_ENV, EXAMPLE, ROOT, load  # noqa: E402

from novelty_probe import dedupe, export, i18n, record, report  # noqa: E402
from novelty_probe.text import DEFAULT_RULES, version_summary  # noqa: E402

merge, authors_script = load("merge"), load("authors")
RAW = EXAMPLE / "results" / "raw"
# 阶段 3 的代码（提交 0beca5e）在示例数据上的合并结果：去掉阶段 4 新增的字段与 bm25（含对数，各平台末位可能不同）后的哈希。
# 2026-11-03 用 git archive 取出阶段 3 的代码实际运行后核对过：新旧结果在这些字段上完全相同（RUN_LOG Step 87）。
PHASE3_PROJECTION = {"": "a2b4ad3c1fdfc030", "_v2": "392d4b04ff1cbd0b"}
NEW_FIELDS = {"authors", "n_authors", "field_source", "dedupe_rules", "bm25"}


def run_main(module, argv):
    out = io.StringIO()
    with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
        rc = module.main()
    return rc, out.getvalue()


def merge_into(d, suffix, raw_files=None):
    """在临时项目目录里跑默认的合并；返回 merged{suffix}.json 的内容。"""
    raw, out = Path(d) / "raw", Path(d) / "merged"
    raw.mkdir(parents=True, exist_ok=True)
    for p in raw_files or RAW.glob(f"*{suffix}.json" if suffix else "*_Q?.json"):
        shutil.copy(p, raw / p.name)
    with mock.patch.object(merge, "RAW_DIR", raw), mock.patch.object(merge, "OUT_DIR", out), \
            mock.patch.object(merge, "ROOT", Path(d)):
        rc, text = run_main(merge, ["merge.py", "--suffix", suffix])
    assert rc == 0, text
    return json.loads((out / f"merged{suffix}.json").read_text(encoding="utf-8"))


def summary(title, year=2024, doi=None, authors=None, abstract=None, arxiv_id=None):
    return version_summary([{"title": title, "year": year, "doi": doi, "arxiv_id": arxiv_id, "venue": None,
                             "abstract": abstract, "authors": authors}], rules=DEFAULT_RULES)


class TestDedupeRules(unittest.TestCase):
    T = "Generative AI narrows the topics that scientists choose to study"

    def decide(self, a, b):
        return dedupe.decide(a, b, DEFAULT_RULES)[:2]

    def test_same_title(self):
        self.assertEqual(self.decide(summary(self.T), summary(self.T, 2025)), ("merge", "D4"))        # 没有作者：与阶段 3 相同
        self.assertEqual(self.decide(summary(self.T, authors=["Ann Lee", "Bo Chen"]),
                                     summary(self.T, authors=["Ann Lee"])), ("merge", "D4"))
        self.assertEqual(self.decide(summary(self.T, authors=["Ann Lee"]), summary(self.T, authors=["Carl Smith"])),
                         ("keep", "R7"))                                                           # 同题、作者完全不同
        self.assertEqual(self.decide(summary(self.T, authors=["Wei Zhang"]), summary(self.T, authors=["Zhang Wei"])),
                         ("merge", "D4"))                                                          # 姓名顺序不同仍算共同的名字
        self.assertEqual(self.decide(summary(self.T, authors=["Ana López"]), summary(self.T, authors=["A. Lopez", "Bo Chen"])),
                         ("merge", "D4"))                                                          # 重音、首字母不影响
        self.assertEqual(self.decide(summary(self.T, authors=["张伟"]), summary(self.T, authors=["Carl Smith"])),
                         ("merge", "D4"))                                                          # 一方没有可比的名字：作者不作证据
        self.assertEqual(self.decide(summary(self.T, doi="10.1/a"), summary(self.T, doi="10.2/b")), ("keep", "R2"))
        self.assertEqual(self.decide(summary(self.T, doi="10.5281/zenodo.1"), summary(self.T)), ("keep", "R3"))
        self.assertEqual(self.decide(summary(self.T, 2010), summary(self.T, 2024)), ("keep", "R4"))

    def test_near_identical_titles_need_shared_authors(self):
        a = "Generative AI narrows the topics that scientists choose to study in physics"
        b = "Generative AI narrows the topics scientists choose to study in physics"
        team, other = ["Ann Lee", "Bo Chen", "Carl Smith"], ["Dan Brown", "Eve Stone"]
        self.assertEqual(self.decide(summary(a), summary(b)), ("keep", "R6"))                       # 没有作者：只记录
        self.assertEqual(self.decide(summary(a, authors=team), summary(b, authors=team[:2])), ("merge", "D5"))
        self.assertEqual(self.decide(summary(a, authors=team), summary(b, authors=["Ann Lee", *other])), ("keep", "R6"))  # 只有一个共同的姓
        self.assertEqual(self.decide(summary(a, authors=["Ann Lee"]), summary(b, authors=["A. Lee", "Bo Chen"])),
                         ("merge", "D5"))                                                          # 一方只有一位作者：一个共同的姓即可
        self.assertEqual(self.decide(summary(a, authors=team, doi="10.1/x"), summary(b, authors=team, doi="10.2/y")),
                         ("keep", "R6"))                                                           # 两个不同的正式 DOI：不并
        self.assertEqual(self.decide(summary(a, authors=["张伟", "李娜"]), summary(b, authors=["张伟", "李娜"])),
                         ("keep", "R6"))                                                           # 没有可比的名字：不并

    def test_cluster_cap(self):
        recs = [{"title": self.T, "year": 2024, "doi": None, "arxiv_id": f"2401.0000{i}", "venue": None, "abstract": None,
                 "authors": None} for i in range(4)]                                       # 四个预印本，题目相同
        roots, _ = dedupe.id_groups(recs)
        final, merges, kept = dedupe.link_versions(recs, roots, DEFAULT_RULES, max_groups=2)
        self.assertEqual(len(set(final)), 2)
        self.assertTrue(kept and all(rule == "R8" for _, _, rule, _ in kept))
        final, _, kept = dedupe.link_versions(recs, roots, DEFAULT_RULES, max_groups=6)
        self.assertEqual((len(set(final)), kept), (1, []))

    def test_id_rules(self):
        recs = [{"doi": "10.31234/osf.io/abcde_v1", "arxiv_id": None}, {"doi": "10.31234/OSF.IO/abcde_v2", "arxiv_id": None},
                {"doi": "10.1/X", "arxiv_id": "2401.00001"}, {"doi": "10.1/x", "arxiv_id": None}, {"doi": None, "arxiv_id": "2401.00001"}]
        roots, links = dedupe.id_groups(recs)
        self.assertEqual(sorted(rule for _, _, rule in links), ["D1", "D2", "D3"])
        self.assertEqual(len(set(roots)), 2)


class TestMergeWithAuthors(unittest.TestCase):
    def test_old_data_unchanged_apart_from_new_fields(self):
        for suffix, expected in PHASE3_PROJECTION.items():
            with self.subTest(run=suffix or "v1"), tempfile.TemporaryDirectory() as d:
                data = merge_into(d, suffix)
                proj = []
                for x in data["records"]:
                    y = {k: v for k, v in x.items() if k not in NEW_FIELDS}
                    y["review"] = [{k: v for k, v in r.items() if k != "rule"} for r in y["review"]]
                    proj.append(y)
                    self.assertIsNone(x["authors"])
                    self.assertTrue(set(x["dedupe_rules"]) <= {"D1", "D2", "D3", "D4"})
                digest = hashlib.sha256(json.dumps(proj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
                self.assertEqual(digest, expected)
                self.assertEqual(data["meta"]["schema"], record.SCHEMA)

    def test_order_independent_and_repeatable(self):
        files = sorted(RAW.glob("*_v2.json"))
        with mock.patch.object(merge, "RAW_DIR", RAW):
            recs, _ = merge.load_raw("_v2")
        for r in recs:
            r["doi"] = record.clean_doi(r["doi"])

        def partition(rs):
            roots, _ = dedupe.id_groups(rs)
            final, _, _ = dedupe.link_versions(rs, roots, DEFAULT_RULES, 6)
            groups = {}
            for r, root in zip(rs, final):
                groups.setdefault(root, set()).add(r["_ref"])
            return {frozenset(g) for g in groups.values()}
        base = partition(recs)
        for seed in (1, 2, 3):
            shuffled = list(recs)
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(partition(shuffled), base, f"seed {seed}")
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            a, b = merge_into(d1, "_v2", files), merge_into(d2, "_v2", files)
        self.assertEqual(a["records"], b["records"])

    def test_authors_flow_from_search_to_merge_csv_and_ris(self):
        cas = ROOT / "tests" / "fixtures" / "cassettes" / "search_q3q4.json"
        search = load("search")
        with tempfile.TemporaryDirectory() as d:
            raw, out = Path(d) / "raw", Path(d) / "merged"
            argv = ["search.py", "--queries", str(EXAMPLE / "queries" / "queries.json"), "--ids", "Q3,Q4",
                    "--cache-dir", str(Path(d) / "cache"), "--http-mode", "replay", "--cassette", str(cas)]
            with mock.patch.object(search, "RAW_DIR", raw):
                self.assertEqual(run_main(search, argv)[0], 0)
            with mock.patch.object(merge, "RAW_DIR", raw), mock.patch.object(merge, "OUT_DIR", out), \
                    mock.patch.object(merge, "ROOT", Path(d)):
                rc, text = run_main(merge, ["merge.py"])
            self.assertEqual(rc, 0, text)
            data = json.loads((out / "merged.json").read_text(encoding="utf-8"))
            csv_text = (out / "candidates.csv").read_text(encoding="utf-8-sig")
            ris = export.parse_ris((out / "candidates.ris").read_text(encoding="utf-8-sig"))
            manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
            report_md = (out / "search_report.md").read_text(encoding="utf-8")
        self.assertEqual(data["meta"]["counts"]["with_authors"], len(data["records"]))
        x = next(r for r in data["records"] if r["n_authors"] and r["n_authors"] > 3)
        self.assertRegex(x["field_source"]["authors"], r"^(openalex|semanticscholar)_Q[34]#\d+$")
        self.assertIn(record.short_authors(x["authors"], x["n_authors"]), csv_text)
        self.assertTrue(record.short_authors(x["authors"], x["n_authors"]).endswith(" et al."))
        self.assertEqual(len(ris), min(len(data["records"]), data["meta"]["candidates"]["top_k"]))
        self.assertTrue(all("AU" in e and "TI" in e and e["TY"][0] in ("JOUR", "UNPB", "GEN") for e in ris))
        self.assertEqual({s["source"] for s in manifest["searches"]}, {"openalex", "semanticscholar"})
        self.assertTrue(all(len(s["sha256"]) == 64 for s in manifest["searches"]))
        self.assertEqual([o["file"].rsplit("/", 1)[-1] for o in manifest["outputs"]],
                         ["merged.json", "candidates.csv", "candidates.ris"])
        for part in ("# 检索报告：v1", "## 检索式", "## 结果数", "## 去重与候选", "doi:10.1186/s13643-020-01542-z"):
            self.assertIn(part, report_md)


class TestRis(unittest.TestCase):
    RECS = [{"merged_id": "M001", "title": "A study\nwith a line break", "authors": ["Ann Lee", "Bo Chen"], "n_authors": 25,
             "year": 2024, "venue": "Nature", "doi": "10.1038/x", "arxiv_id": "2401.00001", "abstract": "Text.",
             "query_ids": ["Q1"], "sources": ["openalex"], "rrf": 0.03, "dedupe_rules": ["D1"]},
            {"merged_id": "M002", "title": "Preprint", "authors": None, "year": 2025, "venue": None,
             "doi": "10.48550/arXiv.2501.00002", "arxiv_id": "2501.00002", "abstract": None},
            {"merged_id": "M003", "title": "No identifier", "authors": [], "year": None, "doi": None, "arxiv_id": None}]

    def test_records_and_types(self):
        text = export.to_ris(self.RECS)
        self.assertTrue(text.startswith("TY  - JOUR\r\n"))
        self.assertNotIn("\n\n", text.replace("\r\n\r\n", "\x00"))          # 只用 CRLF
        recs = export.parse_ris(text)
        self.assertEqual([r["TY"][0] for r in recs], ["JOUR", "UNPB", "GEN"])
        first = recs[0]
        self.assertEqual(first["TI"], ["A study with a line break"])        # 值都在一行
        self.assertEqual(first["AU"], ["Ann Lee", "Bo Chen"])
        self.assertEqual(first["UR"], ["https://doi.org/10.1038/x", "https://arxiv.org/abs/2401.00001"])
        self.assertIn("first 2 of 25 authors", first["N1"][0])
        self.assertIn("queries Q1", first["N1"][0])
        self.assertEqual(first["ID"], ["M001"])
        self.assertNotIn("AU", recs[2])

    def test_written_file_has_bom_and_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.ris"
            export.write_ris(p, self.RECS[:1])
            raw = p.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbfTY  - JOUR\r\n"))
        self.assertTrue(raw.endswith(b"ER  - \r\n"))


class TestReport(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("zh")

    def test_manifest_render_and_diff(self):
        with tempfile.TemporaryDirectory() as d:
            data = merge_into(d, "_v2")
            out = Path(d) / "merged"
            m = json.loads((out / "run_manifest_v2.json").read_text(encoding="utf-8"))
            self.assertEqual(m["schema"], report.SCHEMA)
            self.assertEqual(len(m["searches"]), 12)
            self.assertEqual(m["counts"]["merged_records"], len(data["records"]))
            lm = m["counts"]["local_match"]
            self.assertEqual(set(lm), {"openalex", "semanticscholar"})
            self.assertTrue(all(0 <= v["nonconforming_share"] < 0.5 for v in lm.values()))
            i18n.set_language("en")
            en = report.render_report(m, "_v2")
            self.assertIn("# Search report: v2", en)
            self.assertIn("Local matching bias", en)
            later = json.loads(json.dumps(m))
            later["searches"][0]["sha256"] = "0" * 64
            later["searches"][0]["total_hits"] = 999
            later["candidates"]["items"] = later["candidates"]["items"][1:] + [{"merged_id": "M999", "doi": "10.9/new", "title": "New"}]
            dd = report.diff(m, later)
        self.assertEqual(len(dd["searches"]["changed"]), 1)
        self.assertEqual(dd["searches"]["changed"][0]["total_hits"][1], 999)
        self.assertEqual((len(dd["candidates"]["added"]), len(dd["candidates"]["removed"])), (1, 1))
        self.assertTrue(dd["config"]["same"])

    def test_legacy_writes_no_extra_files(self):
        with tempfile.TemporaryDirectory() as d:
            raw, out = Path(d) / "raw", Path(d) / "merged"
            shutil.copytree(RAW, raw)
            with mock.patch.object(merge, "RAW_DIR", raw), mock.patch.object(merge, "OUT_DIR", out):
                self.assertEqual(run_main(merge, ["merge.py", "--legacy"])[0], 0)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["candidates.csv", "merged.json"])


class TestAuthorsScript(unittest.TestCase):
    def test_uses_search_authors_and_looks_up_only_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            data = merge_into(d, "_v2")
            out = Path(d) / "merged"
            merged = json.loads((out / "merged_v2.json").read_text(encoding="utf-8"))
            for x in merged["records"][:3]:                       # 前三篇假装检索时已带作者
                x["authors"], x["n_authors"] = ["Ann Lee", "Bo Chen"], 2
            ids = {x["merged_id"] for x in merged["records"][:3]}
            (out / "merged_v2.json").write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
            calls = []

            def fake(url, *a, **k):
                calls.append(url)
                return {"id": "W1", "display_name": "T", "authorships": [{"author": {"display_name": "X Y"}}]}
            target = Path(d) / "authors.json"
            with mock.patch.object(authors_script, "get_json", fake):
                rc, text = run_main(authors_script, ["authors.py", "--top", "20", "--candidates", str(out / "candidates_v2.csv"),
                                                     "--out", str(target)])
            res = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0, text)
        by_id = {r["merged_id"]: r for r in res["records"]}
        hit = [by_id[i] for i in ids if i in by_id]
        self.assertTrue(hit and all(r["source"] == "search" and r["authors"] == ["Ann Lee", "Bo Chen"] for r in hit))
        self.assertEqual(res["meta"]["counts"]["from_search"], len(hit))
        self.assertEqual(len(calls), res["meta"]["counts"]["looked_up"] + res["meta"]["counts"]["not_found"])


class TestCommands(unittest.TestCase):
    def run_cmd(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)], capture_output=True,
                              text=True, encoding="utf-8", env=CHILD_ENV)

    def test_export_report_and_qa(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PROJECT.md").write_text("marker\n", encoding="utf-8")
            (root / "results" / "raw").mkdir(parents=True)
            (root / "evidence").mkdir()
            for p in RAW.glob("*_v2.json"):
                shutil.copy(p, root / "results" / "raw" / p.name)
            shutil.copy(EXAMPLE / "evidence" / "evidence_table_v2.md", root / "evidence" / "evidence_table_v2.md")
            r = self.run_cmd("merge.py", "--root", root, "--suffix", "_v2")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = self.run_cmd("export.py", "--root", root, "--suffix", "_v2", "--all")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(export.parse_ris((root / "results" / "merged" / "merged_v2.ris").read_text(encoding="utf-8-sig"))),
                             len(json.loads((root / "results" / "merged" / "merged_v2.json").read_text(encoding="utf-8"))["records"]))
            r = self.run_cmd("export.py", "--root", root, "--suffix", "_v2", "--out", root / "again.ris")
            self.assertEqual(r.returncode, 0, r.stderr)                          # 候选：与合并时写出的相同
            self.assertEqual((root / "again.ris").read_bytes(), (root / "results" / "merged" / "candidates_v2.ris").read_bytes())
            r = self.run_cmd("export.py", "--root", root, "--evidence", root / "evidence" / "evidence_table_v2.md", "--lang", "en")
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = export.parse_ris((root / "evidence" / "evidence_table_v2.ris").read_text(encoding="utf-8-sig"))
            self.assertEqual(len(rows), 10)
            self.assertIn("Research question: overlap", rows[2]["KW"])           # 标注写成关键词
            self.assertIn("evidence table, rank 3", rows[2]["N1"][0])
            manifest = root / "results" / "merged" / "run_manifest_v2.json"
            r = self.run_cmd("report.py", "render", manifest, "--lang", "en")
            self.assertIn("# Search report: v2", r.stdout)
            r = self.run_cmd("report.py", "diff", manifest, manifest, "--lang", "en")
            self.assertIn("search results: 0 added, 0 removed, 0 changed", r.stdout)
            self.assertEqual(json.loads(r.stdout.splitlines()[-1])["summary"],
                             {"changed_searches": 0, "new_candidates": 0, "dropped_candidates": 0})
            r = self.run_cmd("qa.py", "--root", root, "--suffix", "_v2")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("本地匹配的偏差 openalex", r.stdout)


if __name__ == "__main__":
    unittest.main()
