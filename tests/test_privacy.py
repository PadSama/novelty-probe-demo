#!/usr/bin/env python3
"""隐私与数据条款的护栏：录制件不留电子邮件地址；仓库里的数据与文档不含邮件地址；运行日志不写用户目录；
检索报告注明数据来源与条款。不联网。"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import ROOT  # noqa: E402

from novelty_probe import cache, i18n, report  # noqa: E402
from novelty_probe.commands import logrun  # noqa: E402

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ALLOWED = ("noreply@anthropic.com", "users.noreply.github.com", "@example.org", "@example.com")
SKIP_DIRS = {".git", ".cache", "__pycache__", "build", "dist"}


class TestCassetteRedaction(unittest.TestCase):
    def test_emails_are_removed_when_recording(self):
        body = json.dumps({"results": [{"raw_affiliation_strings": ["Dept. X, jane.doe@example.org", "plain"]}]})
        with tempfile.TemporaryDirectory() as d:
            c = cache.Cassette(Path(d) / "c.json")
            c.record({"key": "k", "request": {"url": "u"}, "response": {"status": 200, "body": body}})
            c.record({"key": "h", "request": {"url": "u2"}, "response": {"status": 200, "body": "<p>mail a.b@example.org</p>"}})
            saved = json.loads((Path(d) / "c.json").read_text(encoding="utf-8"))
        bodies = [it["response"]["body"] for it in saved["interactions"]]
        self.assertEqual(json.loads(bodies[0])["results"][0]["raw_affiliation_strings"][0],
                         "Dept. X, " + cache.EMAIL_PLACEHOLDER)          # JSON 仍合法，转义字符不受影响
        self.assertEqual(bodies[1], "<p>mail " + cache.EMAIL_PLACEHOLDER + "</p>")
        self.assertEqual(saved["redacted_in_bodies"], ["email addresses"])
        self.assertEqual(cache.redact_emails("no address here"), "no address here")


class TestRepositoryHasNoEmailAddresses(unittest.TestCase):
    """仓库公开：数据、录制件与文档里不应出现个人的电子邮件地址（作者单位字符串里的通讯作者邮箱也算）。"""

    def test_scan(self):
        offenders = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if not name.endswith((".json", ".md", ".csv", ".ris", ".txt", ".cff", ".toml", ".yml", ".py")):
                    continue
                path = Path(dirpath) / name
                text = path.read_text(encoding="utf-8", errors="replace")
                for m in EMAIL.finditer(text):
                    if not any(a in m.group(0) for a in ALLOWED) and "@" + "example" not in m.group(0):
                        offenders.append(f"{path.relative_to(ROOT)}: {m.group(0)[:3]}…")
        self.assertEqual(offenders, [])


class TestRunLogPrivacy(unittest.TestCase):
    def test_home_directory_is_written_as_tilde(self):
        home = Path(tempfile.gettempdir()) / "alice"
        with mock.patch.object(Path, "home", return_value=home):
            text = f"cd {home / 'research'} && ls {home}2 {home}"
            self.assertEqual(logrun.mask_home(text), f"cd ~{os.sep}research && ls {home}2 ~")
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / "PROJECT.md").write_text("x\n", encoding="utf-8")
                code, _ = logrun.run_logged("privacy", [sys.executable, "-c", f"print({str(home / 'x')!r})"], d,
                                            display=["novelty-probe", "search", "--queries", str(home / "q.json")],
                                            echo=False)
                log = (Path(d) / "logs" / "RUN_LOG.md").read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertNotIn(str(home), log)
        self.assertIn(f"~{os.sep}q.json", log)


class TestReportCreditsSources(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("zh")

    def test_data_sources_section(self):
        m = {"created_at": "t", "tool": {"novelty_probe": "x", "python": "3"}, "config": {}, "parameters": {"rrf_k": 60},
             "searches": [{"source": s, "query_id": "Q1", "query_original": "a AND b", "query_sent": "a AND b",
                           "retrieved_at": "2026-11-03T00:00:00", "total_hits": 1, "returned": 1}
                          for s in ("openalex", "semanticscholar")],
             "outputs": [], "counts": {"raw_records": 2, "merged_records": 1, "duplicates_removed": 1},
             "candidates": {"top_k": 20, "sort": "x", "items": []}}
        i18n.set_language("en")
        text = report.render_report(m)
        section = text[text.index("## Data sources and terms"):text.index("## Files")]
        self.assertIn("https://www.semanticscholar.org/?utm_source=api", section)   # S2 许可协议要求的链接
        self.assertIn("CC0", section)
        self.assertNotIn("Crossref", section)                                     # 只列本次用到的来源
        self.assertIn("Abstracts remain the copyright", section)


class TestProjectGitignore(unittest.TestCase):
    def test_init_ignores_cache_and_explains_results(self):
        text = (ROOT / "novelty_probe" / "templates" / "gitignore.txt").read_text(encoding="utf-8")
        self.assertIn(".cache/", text.splitlines())                                # 原始的 API 响应不进仓库
        self.assertIn("# results/", text)                                           # 公开仓库时的提示


if __name__ == "__main__":
    unittest.main()
