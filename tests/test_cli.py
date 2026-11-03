#!/usr/bin/env python3
"""阶段 5：novelty-probe 命令（分发、--log、旧入口转发）、项目目录查找、novelty-probe init、novelty-probe run。不联网。"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import CHILD_ENV, EXAMPLE, ROOT, SCRIPTS  # noqa: E402

from novelty_probe import __version__, paths, runtime  # noqa: E402
from novelty_probe.commands import init as init_cmd  # noqa: E402

CASSETTES = ROOT / "tests" / "fixtures" / "cassettes"
TEMPLATES = ROOT / "novelty_probe" / "templates"


def np(*args, cwd=None, env=None):
    """python -m novelty_probe …（与安装后的 novelty-probe 命令相同）。"""
    return subprocess.run([sys.executable, "-m", "novelty_probe", *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd, env={**CHILD_ENV, **(env or {})})


def steps_in(log_text):
    return re.findall(r"^## \[[^\]]*\] (Step \d+ — .*)$", log_text, re.M)


def new_project(d, queries=None):
    """在临时目录里 init 一个项目；queries：要写进 queries/queries.json 的检索式（从教程 v1 取）。"""
    p = Path(d) / "proj"
    r = np("init", p)
    assert r.returncode == 0, r.stderr
    if queries:
        q = json.loads((EXAMPLE / "queries" / "queries.json").read_text(encoding="utf-8"))
        (p / "queries" / "queries.json").write_text(json.dumps([x for x in q if x["id"] in queries], ensure_ascii=False),
                                                    encoding="utf-8")
    return p


class TestDispatch(unittest.TestCase):
    def test_version_help_and_unknown_command(self):
        r = np("--version")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"novelty-probe {__version__}"))
        r = np(cwd=ROOT)
        self.assertEqual(r.returncode, 0)
        for name in ("init", "run", "search", "merge", "verify", "logrun"):
            self.assertRegex(r.stdout, rf"\n  {name} ")
        r = np("frobnicate")
        self.assertEqual(r.returncode, 2)
        self.assertIn("frobnicate", r.stderr)
        r = np("merge", "--help", env={"NP_LANG": "en"})
        self.assertIn("usage: novelty-probe merge", r.stdout)

    def test_old_scripts_forward_to_the_same_command(self):
        q = EXAMPLE / "queries" / "queries.json"
        a = subprocess.run([sys.executable, str(SCRIPTS / "search.py"), "--dry-run", "--queries", str(q)], capture_output=True,
                           text=True, encoding="utf-8", cwd=ROOT, env=CHILD_ENV)
        b = np("search", "--dry-run", "--queries", q, cwd=ROOT)
        self.assertEqual((a.returncode, a.stdout), (b.returncode, b.stdout))
        self.assertIn("6/6", b.stdout)

    def test_log_option_writes_numbered_entry_without_local_paths(self):
        with tempfile.TemporaryDirectory() as d:
            p = new_project(d)
            r = np("config", "check", "--log", "检查配置", cwd=p)
            self.assertEqual(r.returncode, 0, r.stderr)
            log = (p / "logs" / "RUN_LOG.md").read_text(encoding="utf-8")
            self.assertEqual(steps_in(log)[-1], "Step 1 — 检查配置")
            self.assertIn("novelty-probe config check\n# argv: [\"novelty-probe\", \"config\", \"check\"]", log)
            self.assertNotIn(sys.executable, log)                        # 不写本机的解释器路径
            self.assertEqual(np("run", "--log", "x", cwd=p).returncode, 2)  # run / logrun 自己写日志


class TestProjectRoot(unittest.TestCase):
    def test_installed_package_does_not_fall_back_to_its_own_location(self):
        with tempfile.TemporaryDirectory() as site, tempfile.TemporaryDirectory() as elsewhere:
            with mock.patch.object(paths, "PACKAGE_ROOT", Path(site)):     # 安装后：包所在目录不是项目
                with self.assertRaises(paths.ProjectNotFound):
                    paths.find_root(env={}, start=elsewhere)
                (Path(elsewhere) / "PROJECT.md").write_text("x\n", encoding="utf-8")
                self.assertEqual(paths.find_root(env={}, start=Path(elsewhere) / "sub"), Path(elsewhere).resolve())
        self.assertEqual(paths.find_root(env={}, start=tempfile.gettempdir()), paths.PACKAGE_ROOT)   # 源码仓库照旧

    def test_bind_root_only_moves_other_projects(self):
        g = {"ROOT": ROOT, "RAW_DIR": ROOT / "results" / "raw"}
        self.assertFalse(runtime.bind_root(g, ROOT, {"RAW_DIR": "results/raw"}))
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(runtime.bind_root(g, d, {"RAW_DIR": "results/raw"}))
            self.assertEqual(g["RAW_DIR"], Path(d).resolve() / "results" / "raw")


class TestInit(unittest.TestCase):
    def test_creates_project_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            p = new_project(d)
            for f in ("PROJECT.md", "AGENTS.md", "HOWTO.md"):
                self.assertEqual((p / f).read_bytes(), (TEMPLATES / f).read_bytes(), f)
            for sub in ("facets", "queries", "results/raw", "results/merged", "evidence"):
                self.assertTrue((p / sub).is_dir(), sub)
            cfg = json.loads((p / "novelty-probe.json").read_text(encoding="utf-8"))
            self.assertEqual(cfg["contact_email"], "")                    # 不代填个人信息
            self.assertIn(".cache/", (p / ".gitignore").read_text(encoding="utf-8"))
            log = (p / "logs" / "RUN_LOG.md").read_text(encoding="utf-8")
            self.assertEqual(steps_in(log), ["Step 0 — 新建项目（novelty-probe init）"])
            self.assertIn("novelty-probe init proj\n", log)               # 只记目录名，不记本机的绝对路径
            self.assertEqual(np("config", "check", cwd=p).returncode, 0)

            (p / "idea" / "idea.md").write_text("我的想法\n", encoding="utf-8")
            (p / "HOWTO.md").write_text("old\n", encoding="utf-8")
            r = np("init", p)
            self.assertEqual(r.returncode, 0)
            self.assertEqual((p / "idea" / "idea.md").read_text(encoding="utf-8"), "我的想法\n")
            self.assertEqual((p / "HOWTO.md").read_text(encoding="utf-8"), "old\n")
            self.assertEqual(len(steps_in((p / "logs" / "RUN_LOG.md").read_text(encoding="utf-8"))), 1)  # 什么都没写：不记日志

            r = np("init", p, "--update-docs")
            self.assertEqual((p / "HOWTO.md").read_bytes(), (TEMPLATES / "HOWTO.md").read_bytes())
            self.assertEqual((p / "idea" / "idea.md").read_text(encoding="utf-8"), "我的想法\n")   # 研究者的文件不动
            self.assertEqual(steps_in((p / "logs" / "RUN_LOG.md").read_text(encoding="utf-8"))[-1],
                             "Step 1 — 刷新文档（novelty-probe init --update-docs）")

    def test_refuses_a_project_inside_the_source_repository(self):
        self.assertTrue(init_cmd.inside_source_repo(ROOT / "examples" / "mine"))
        self.assertFalse(init_cmd.inside_source_repo(ROOT))
        r = np("init", ROOT / "examples" / "should-not-exist", env={"NP_LANG": "en"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("--force", r.stderr)
        self.assertFalse((ROOT / "examples" / "should-not-exist").exists())

    def test_repository_docs_equal_the_templates(self):
        """仓库根目录（教程示例）与新项目用同一套规则、说明与指南：改了一份就要同步另一份。"""
        for f in ("PROJECT.md", "AGENTS.md", "HOWTO.md"):
            self.assertEqual((ROOT / f).read_bytes(), (TEMPLATES / f).read_bytes(),
                             f"{f} 与 novelty_probe/templates/{f} 不同：改动后请复制到另一处")


class TestRun(unittest.TestCase):
    def combined_cassette(self, d):
        """检索（v1 Q3、Q4）与补摘要的录制件合成一份：run 把同一个 --cassette 传给各个联网的步骤。"""
        out = Path(d) / "run.json"
        parts = [json.loads((CASSETTES / f).read_text(encoding="utf-8")) for f in ("search_q3q4.json", "enrich_q3q4.json")]
        out.write_text(json.dumps({**parts[0], "interactions": parts[0]["interactions"] + parts[1]["interactions"]}),
                       encoding="utf-8")
        return out

    def test_all_steps_from_recorded_responses(self):
        with tempfile.TemporaryDirectory() as d:
            p = new_project(d, queries=("Q3", "Q4"))
            r = np("run", "--http-mode", "replay", "--cassette", self.combined_cassette(d), cwd=p)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr)
            log = (p / "logs" / "RUN_LOG.md").read_text(encoding="utf-8")
            self.assertEqual(steps_in(log), ["Step 0 — 新建项目（novelty-probe init）", "Step 1 — T3 检查检索式",
                                             "Step 2 — T3 检索", "Step 3 — T3 质量检查", "Step 4 — T4 合并去重",
                                             "Step 5 — T5 补摘要"])           # 候选都带作者：跳过补查作者
            self.assertIn("[authors]", r.stdout)
            self.assertIn("novelty-probe search --queries queries/queries.json --http-mode replay", log)
            self.assertNotIn(sys.executable, log)
            for f in ("results/merged/candidates.csv", "results/merged/candidates.ris", "results/merged/search_report.md",
                      "results/merged/run_manifest.json", "evidence/enrichment.json"):
                self.assertTrue((p / f).is_file(), f)
            self.assertEqual(json.loads((p / "evidence" / "enrichment.json").read_text(encoding="utf-8"))["meta"]["counts"]
                             ["candidates"], 13)

    def test_dry_run_stop_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            p = new_project(d, queries=("Q3", "Q4"))
            r = np("run", "--dry-run", cwd=p)
            self.assertEqual(r.returncode, 0)
            self.assertEqual([l.split()[0] for l in r.stdout.splitlines()[1:]], ["check", "search", "qa", "merge", "authors",
                                                                               "enrich"])
            self.assertEqual(len(steps_in((p / "logs" / "RUN_LOG.md").read_text(encoding="utf-8"))), 1)   # 只打印，不运行

            (p / "queries" / "queries.json").write_text('[{"id": "Q1", "facets_used": [], "purpose": "component", '
                                                        '"query": "a OR b"}]', encoding="utf-8")
            r = np("run", "--http-mode", "replay", "--cassette", self.combined_cassette(d), cwd=p, env={"NP_LANG": "en"})
            self.assertEqual(r.returncode, 1)                                 # 检索式不合格：停在 check
            self.assertIn("novelty-probe run --http-mode replay", r.stderr)
            self.assertIn("--from check", r.stderr)
            self.assertEqual(steps_in((p / "logs" / "RUN_LOG.md").read_text(encoding="utf-8"))[-1], "Step 1 — T3 check the queries")
            self.assertFalse(any((p / "results" / "raw").iterdir()))

            (p / "queries" / "queries.json").unlink()
            r = np("run", cwd=p)
            self.assertEqual(r.returncode, 2)
            self.assertIn("queries/queries.json", r.stderr)
            r = np("run", "--from", "merge", "--to", "qa", cwd=p)
            self.assertEqual(r.returncode, 2)                                 # --from 在 --to 之后

    def test_missing_authors_counts(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "c.csv"
            f.write_text("rank,merged_id,doi,authors\n1,M1,10.1/a,A B\n2,M2,10.1/b,\n3,M3,,\n", encoding="utf-8")
            from novelty_probe.commands import run as run_cmd
            self.assertEqual(run_cmd.missing_authors(f, 20), 1)              # 缺作者且有 DOI 的才补查
            f.write_text("rank,merged_id,doi\n1,M1,10.1/a\n2,M2,\n", encoding="utf-8")
            self.assertEqual(run_cmd.missing_authors(f, 20), 1)              # 旧格式（没有 authors 列）


if __name__ == "__main__":
    unittest.main()
