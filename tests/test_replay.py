#!/usr/bin/env python3
"""用录制的真实 API 响应（tests/fixtures/cassettes/，2026-11-02 录制）离线回放整条脚本流程，并逐条校验响应形状。

录制件由 scripts 以 --http-mode record 生成，已去掉密钥；回放模式禁网，缺少录制条目会抛 ReplayMiss。
重新录制：python3 scripts/search.py --queries examples/tutorial/queries/queries.json --ids Q3,Q4 --suffix _rec \\
            --http-mode record --cassette tests/fixtures/cassettes/search_q3q4.json（其余见各测试的 argv）。
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import EXAMPLE, ROOT, load  # noqa: E402

from novelty_probe import http, schemas  # noqa: E402

search, verify, snowball = load("search"), load("verify"), load("snowball")
CASSETTES = ROOT / "tests" / "fixtures" / "cassettes"


def replay_args(name):
    return ["--http-mode", "replay", "--cassette", str(CASSETTES / name)]


class TestReplaySearch(unittest.TestCase):
    def test_search_q3_q4_from_cassette(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "raw"
            argv = ["search.py", "--queries", str(EXAMPLE / "queries" / "queries.json"), "--ids", "Q3,Q4", "--suffix", "_rec",
                    "--cache-dir", str(Path(d) / "cache"), *replay_args("search_q3q4.json")]
            with mock.patch.object(search, "RAW_DIR", raw), mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(search.main(), 0, out.getvalue())
            files = sorted(p.name for p in raw.glob("*.json"))
            self.assertEqual(files, ["openalex_Q3_rec.json", "openalex_Q4_rec.json", "semanticscholar_Q3_rec.json",
                                     "semanticscholar_Q4_rec.json"])
            oa = json.loads((raw / "openalex_Q3_rec.json").read_text(encoding="utf-8"))
            s2 = json.loads((raw / "semanticscholar_Q3_rec.json").read_text(encoding="utf-8"))
            self.assertEqual((oa["meta"]["total_hits"], len(oa["records"])), (8, 8))
            self.assertEqual((s2["meta"]["total_hits"], len(s2["records"])), (9, 9))
            self.assertEqual(oa["meta"]["warnings"], [])                       # 形状校验与解析核对都通过
            self.assertIn("filter_rows", oa["meta"]["api_parse_tree"])
            self.assertEqual(oa["meta"]["http"]["mode"], "replay")
            self.assertTrue(all("local_rank" in r for r in s2["records"]))
            for f in files:
                self.assertEqual(schemas.raw_results_file(json.loads((raw / f).read_text(encoding="utf-8"))), [], f)


class TestReplayVerify(unittest.TestCase):
    def test_verify_three_rows_from_cassette(self):
        with tempfile.TemporaryDirectory() as d:
            table = Path(d) / "t.md"
            shutil.copy(ROOT / "tests" / "fixtures" / "verify_table_recorded.md", table)
            argv = ["verify.py", "--table", str(table), "--no-landing", "--cache-dir", str(Path(d) / "cache"),
                    *replay_args("verify_3rows.json")]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                rc = verify.main()
            cells = {}
            for l in table.read_text(encoding="utf-8").splitlines():
                r = verify.split_row(l)
                if r and r[0].isdigit():
                    cells[r[0]] = r[-1]
        self.assertEqual(rc, 0)
        self.assertEqual(cells["1"], "Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the "
                                     "collective diversity of novel content；落地页 skipped")
        self.assertEqual(cells["2"], "Crossref 无记录（Datacite 登记的 DOI）；OpenAlex · 题目一致 · A systematic review of research "
                                     "on large language models for computer programming education；落地页 skipped")
        self.assertTrue(cells["3"].startswith("Crossref HTTP 200 · 题目一致 · Work–life balance"))


class TestReplaySnowball(unittest.TestCase):
    def run_snowball(self, d, cassette, *extra):
        out = Path(d) / "out"
        argv = ["snowball.py", "--seeds", "10.1145/3635636.3656204", "--queries", str(EXAMPLE / "queries" / "queries.json"),
                "--suffix", "_rec", "--max-forward", "30", "--top", "5", "--keep", "50",
                "--cache-dir", str(Path(d) / "cache"), *replay_args(cassette), *extra]
        with mock.patch.object(snowball, "RAW_DIR", out), mock.patch.object(snowball, "OUT_DIR", out), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(snowball.main(), 0)
        return out

    def test_onehop_from_cassette(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.run_snowball(d, "snowball_onehop.json")
            data = json.loads((out / "chase_C1_rec.json").read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["total_hits"], 79)                   # 50 条参考文献 + 30 篇引用者 − 种子的版本
            self.assertEqual(len(data["records"]), 50)                          # --keep 50
            self.assertEqual(data["records"][0]["doi"], "10.1145/3706598.3713146")
            self.assertTrue((out / "chase_C1_rec.csv").is_file())

    def test_cocite_from_cassette(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.run_snowball(d, "snowball_cocite.json", "--cocite", "--citer-filter", "scientist*")
            data = json.loads((out / "chase_C2_rec.json").read_text(encoding="utf-8"))
            m = data["meta"]
            self.assertEqual((m["citing_total_unfiltered"], m["citing_filtered"], m["citers_used"], m["cocited_kept"]), (185, 1, 1, 0))


class TestCassetteContracts(unittest.TestCase):
    """录制件里的每个真实响应都要符合 schemas 里写下的形状；API 改字段时这里先失败。"""

    def test_recorded_bodies_match_schemas(self):
        checked = 0
        for path in sorted(CASSETTES.glob("*.json")):
            for it in json.loads(path.read_text(encoding="utf-8"))["interactions"]:
                url, status, body = it["request"]["url"], it["response"]["status"], it["response"].get("body")
                if status != 200 or not body:
                    continue
                obj = json.loads(body)
                if "api.openalex.org/works?" in url:
                    w = schemas.openalex_list(obj)
                elif "api.openalex.org/works/doi:" in url:
                    w = schemas.openalex_work(obj)
                elif "/paper/search/bulk" in url:
                    w = schemas.s2_bulk(obj)
                elif url.endswith("/agency"):
                    w = schemas.crossref_agency(obj)
                elif "api.crossref.org/works?" in url:
                    w = schemas.crossref_list(obj)
                elif "api.crossref.org" in url or "doi.org/" in url:
                    w = schemas.csl_json(obj)
                else:
                    continue
                self.assertEqual(w, [], f"{path.name}: {url[:80]}")
                checked += 1
        self.assertGreaterEqual(checked, 10)

    def test_replay_refuses_unrecorded_requests(self):
        c = http.Client("replay", cassette=str(CASSETTES / "search_q3q4.json"), env={"NP_HTTP_CACHE": tempfile.mkdtemp()})
        with self.assertRaises(http.ReplayMiss):
            c.get_json("https://api.openalex.org/works?filter=title_and_abstract.search:unrecorded")


if __name__ == "__main__":
    unittest.main()
