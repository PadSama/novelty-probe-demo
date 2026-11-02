#!/usr/bin/env python3
"""novelty_probe 核心层的离线测试：文件读写、路径显示、面标签别名。不联网。"""
import io as _io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import ROOT, load  # noqa: E402

from novelty_probe import defaults, io, paths  # noqa: E402

snowball = load("snowball")


class TestIO(unittest.TestCase):
    def test_lenient_json_accepts_bom_and_fences(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "q.json"
            p.write_bytes(b"\xef\xbb\xbf" + json.dumps([{"id": "Q1"}]).encode())
            self.assertEqual(io.load_json_lenient(p), [{"id": "Q1"}])
            p.write_text("```json\n[1, 2]\n```\n", encoding="utf-8")
            self.assertEqual(io.load_json_lenient(p), [1, 2])
            p.write_text("[1,", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "不是合法的 JSON"):
                io.load_json_lenient(p)

    def test_writes_use_lf_and_are_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "out.json"
            io.write_json(p, {"a": "中文", "b": [1]})
            raw = p.read_bytes()
            self.assertNotIn(b"\r\n", raw)
            self.assertIn("中文".encode("utf-8"), raw)                 # ensure_ascii=False
            self.assertEqual(json.loads(raw.decode("utf-8")), {"a": "中文", "b": [1]})
            self.assertEqual([x.name for x in p.parent.iterdir()], ["out.json"])   # 没有残留的临时文件
            io.write_text(p, "x\ny\n")
            self.assertEqual(p.read_bytes(), b"x\ny\n")
            io.append_text(p, "z\n")
            self.assertEqual(p.read_bytes(), b"x\ny\nz\n")

    def test_atomic_write_leaves_old_file_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.txt"
            io.write_text(p, "old")
            with mock.patch("os.replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
                io.atomic_write_text(p, "new")
            self.assertEqual(p.read_text(encoding="utf-8"), "old")
            self.assertEqual([x.name for x in Path(d).iterdir()], ["f.txt"])

    def test_configure_console_tolerates_streams_without_reconfigure(self):
        fake = _io.StringIO()
        with mock.patch.object(sys, "stdout", fake), mock.patch.object(sys, "stderr", fake):
            io.configure_console()                                      # StringIO 没有 reconfigure：不报错
        io.configure_console()                                          # 真实流：可重复调用


class TestPaths(unittest.TestCase):
    def test_rel_uses_posix_separators_inside_root(self):
        self.assertEqual(paths.rel(ROOT / "results" / "raw" / "x.json", ROOT), "results/raw/x.json")
        outside = Path(tempfile.gettempdir()) / "elsewhere.json"
        self.assertTrue(Path(paths.rel(outside, ROOT)).is_absolute())

    def test_find_root_precedence(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d).resolve()
            (d / "PROJECT.md").write_text("x", encoding="utf-8")
            (d / "deep" / "er").mkdir(parents=True)
            self.assertEqual(paths.find_root(start=d / "deep" / "er", env={}), d)          # 向上找标记文件
            self.assertEqual(paths.find_root(env={"NOVELTY_PROBE_ROOT": str(d / "deep")}), d / "deep")
            self.assertEqual(paths.find_root(explicit=d / "deep" / "er", env={}), d / "deep" / "er")
            self.assertEqual(paths.find_root(start=Path(tempfile.gettempdir()), env={}), paths.PACKAGE_ROOT)


class TestFacetAliases(unittest.TestCase):
    ROW = "| 2 | A | 2024 | T | doi:10.1126/sciadv.adn5290 · arXiv:2312.00506 | overlap | overlap | differ | differ | overlap | x |"

    def test_facet_columns_accept_either_language(self):
        zh = ["rank", "作者", "年份", "题目", "DOI/arXiv", "研究问题", "作用机制", "研究情境", "数据与方法", "预期发现", "verified"]
        en = ["rank", "Authors", "Year", "Title", "DOI/arXiv", "Research question", "Mechanism", "Context",
              "Data and methods", "Expected findings", "verified"]
        self.assertEqual(defaults.facet_columns(zh), defaults.facet_columns(en))
        self.assertEqual(defaults.facet_columns(zh)["context"], 7)
        self.assertEqual(defaults.find_column(en, "title"), 3)
        self.assertIsNone(defaults.find_column(["a"], "title"))

    def test_snowball_seeds_from_english_table(self):
        for header in ("| rank | 作者 | 年份 | 题目 | DOI/arXiv | 研究问题 | 作用机制 | 研究情境 | 数据与方法 | 预期发现 | verified |",
                       "| rank | Authors | Year | Title | DOI/arXiv | Research question | Mechanism | Context | "
                       "Data and methods | Expected findings | verified |"):
            with self.subTest(header=header[:30]), tempfile.TemporaryDirectory() as d:
                p = Path(d) / "t.md"
                p.write_text("\n".join([header, "|---" * 11 + "|", self.ROW]) + "\n", encoding="utf-8")
                self.assertEqual(snowball.seeds_from_evidence(p, 2), [("rank 2", "10.1126/sciadv.adn5290", "2312.00506")])


class TestCompatibility(unittest.TestCase):
    """静态检查：不使用 Python 3.9 没有的接口（本项目支持 3.9+；CI 以外的环境里只能这样把关）。"""
    PATTERNS = [
        (r"\.write_text\([^)]*newline=", "Path.write_text(newline=) 需要 3.10+，用 open(..., newline=) 代替"),
        (r"\.removeprefix\(|\.removesuffix\(", "str.removeprefix/removesuffix 需要 3.9+（可用，但请确认不是 3.8 环境）"),
        (r"^\s*match\s+\w+.*:\s*$", "match 语句需要 3.10+"),
        (r"zip\([^)]*strict=", "zip(strict=) 需要 3.10+"),
        (r"\bint\s*\|\s*None\b|\bstr\s*\|\s*None\b|\bdict\s*\|\s*None\b", "X | None 类型写法需要 3.10+（在运行时求值的位置）"),
        (r"\bfrom zoneinfo import|\bimport tomllib\b", "zoneinfo / tomllib 需要 3.9+/3.11+"),
    ]

    def test_no_python_310_only_apis(self):
        import re
        offenders = []
        for folder in ("novelty_probe", "scripts"):
            for f in sorted((ROOT / folder).glob("*.py")):
                for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    for pat, why in self.PATTERNS:
                        if re.search(pat, line) and "removeprefix" not in pat:
                            offenders.append(f"{f.relative_to(ROOT)}:{i}: {why}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
