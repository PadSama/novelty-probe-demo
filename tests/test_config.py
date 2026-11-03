#!/usr/bin/env python3
"""配置层（novelty_probe/config.py、runtime.py）与界面语言（i18n.py）的离线测试。不联网。"""
import contextlib
import io as _io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import CHILD_ENV, EXAMPLE, ROOT, load  # noqa: E402

from novelty_probe import config, defaults, i18n, runtime  # noqa: E402
from novelty_probe.http import POLICIES  # noqa: E402

search, merge, textmatch = load("search"), load("merge"), load("textmatch")


def write_cfg(d, data):
    path = Path(d) / config.CONFIG_NAME
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class LanguageReset(unittest.TestCase):
    """每个测试之后把界面语言恢复为中文，免得影响其他测试里的中文断言。"""

    def tearDown(self):
        i18n.set_language("zh")


class TestLoadAndMerge(LanguageReset):
    def test_defaults_without_file(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = config.load_config(root=d, env={})
        self.assertIsNone(cfg.file)
        self.assertEqual(cfg.warnings, [])
        self.assertEqual(cfg.hash, config.defaults().hash)
        self.assertEqual(cfg["merge"]["top_k"], 20)
        self.assertEqual(cfg["facets"], defaults.FACETS)

    def test_repository_config_changes_nothing(self):
        cfg = config.load_config(root=ROOT, env={})
        self.assertEqual(cfg.file, ROOT / config.CONFIG_NAME)
        self.assertEqual(cfg.warnings, [])
        self.assertEqual(config.diff(cfg), {})                 # 仓库里的配置文件不改变任何参数
        self.assertEqual(cfg.hash, config.defaults().hash)
        self.assertEqual(cfg["contact_email"], "")             # 助手不代填邮箱

    def test_override_extend_comments_unknown_keys(self):
        with tempfile.TemporaryDirectory() as d:
            write_cfg(d, {"_note": "comment", "merge": {"top_k": 30, "bm25": {"b": 0.5}},
                          "versions": {"preprint_doi_prefixes_extend": ["10.9999/", "10.1101/"]},
                          "textmatch": {"stopwords_extend": ["model"]},
                          "labels": ["overlap", "partial", "differ", "unknown"],
                          "queries": {"truncation": {"theor*": "theory"}, "purposes": {"background": {"year_from": None}}},
                          "compare": {"marker_terms": {"bio": ["CRISPR"]}},
                          "sources": {"openalex": {"top_n": 50}},
                          "bogus": 1})
            cfg = config.load_config(root=d, env={})
        self.assertEqual(cfg["merge"]["top_k"], 30)
        self.assertEqual(cfg["merge"]["bm25"], {"k1": 1.2, "b": 0.5})          # 对象逐层合并
        prefixes = cfg["versions"]["preprint_doi_prefixes"]
        self.assertEqual(prefixes[-1], "10.9999/")                              # _extend 追加
        self.assertEqual(prefixes.count("10.1101/"), 1)                         # 已有的不重复
        self.assertIn("model", cfg["textmatch"]["stopwords"])
        self.assertEqual(cfg["labels"], ["overlap", "partial", "differ", "unknown"])   # 列表整体替换
        self.assertEqual(cfg["queries"]["truncation"]["theor*"], "theory")
        self.assertIn("scientist*", cfg["queries"]["truncation"])               # 用户自定义的对象与默认值取并集
        self.assertEqual(cfg["queries"]["purposes"]["concurrent"], {"year_from": 2023})
        self.assertEqual(cfg["compare"]["marker_terms"]["bio"], ["CRISPR"])
        self.assertEqual(cfg["sources"]["openalex"], {"enabled": True, "top_n": 50})
        self.assertNotIn("_note", cfg)
        self.assertEqual(len(cfg.warnings), 1)
        self.assertIn("bogus", cfg.warnings[0])
        self.assertNotEqual(cfg.hash, config.defaults().hash)

    def test_validation_lists_every_problem_in_both_languages(self):
        bad = {"merge": {"top_k": 0}, "labels": ["same", "different"], "queries": {"truncation": {"foo": "bar"}},
               "sources": {"openalex": {"top_n": 500}}, "versions": {"year_window": -1}}
        with tempfile.TemporaryDirectory() as d:
            write_cfg(d, bad)
            with self.assertRaises(config.ConfigError) as zh:
                config.load_config(root=d, env={})
            i18n.set_language("en")
            with self.assertRaises(config.ConfigError) as en:
                config.load_config(root=d, env={})
        for text, words in ((str(zh.exception), ("merge.top_k", "labels", "'foo'", "top_n", "year_window", "配置有问题")),
                            (str(en.exception), ("merge.top_k", "labels", "'foo'", "top_n", "year_window", "Problems"))):
            for w in words:
                self.assertIn(w, text)

    def test_bad_json_and_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / config.CONFIG_NAME).write_text('{"merge": ', encoding="utf-8")
            with self.assertRaisesRegex(config.ConfigError, "不是合法的 JSON"):
                config.load_config(root=d, env={})
            with self.assertRaisesRegex(config.ConfigError, "找不到配置文件"):
                config.load_config(Path(d) / "none.json", env={})

    def test_hash_ignores_email_and_language(self):
        with tempfile.TemporaryDirectory() as d:
            write_cfg(d, {"contact_email": "someone@example.org", "language": "en"})
            cfg = config.load_config(root=d, env={})
        self.assertEqual(cfg.hash, config.defaults().hash)

    def test_lookup_order(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as e:
            root_file = write_cfg(d, {"merge": {"top_k": 7}})
            env_file = write_cfg(e, {"merge": {"top_k": 8}})
            self.assertEqual(config.find_config_file(None, d, {}), root_file)
            self.assertEqual(config.find_config_file(None, d, {"NOVELTY_PROBE_CONFIG": str(env_file)}), env_file)
            self.assertEqual(config.find_config_file(str(root_file), d, {"NOVELTY_PROBE_CONFIG": str(env_file)}), root_file)
            self.assertEqual(config.load_config(root=d, env={"NOVELTY_PROBE_CONFIG": str(env_file)})["merge"]["top_k"], 8)


class TestRuntime(LanguageReset):
    def test_http_policy_override(self):
        cfg = config.defaults()
        cfg["http"]["policies"] = {"api.semanticscholar.org": {"min_interval_s": 2.5}}
        pol = runtime.policies_from_config(cfg)
        self.assertEqual(pol["api.semanticscholar.org"].min_interval_s, 2.5)
        self.assertEqual(pol["api.semanticscholar.org"].max_attempts, POLICIES["api.semanticscholar.org"].max_attempts)
        cfg["http"]["policies"] = {"api.openalex.org": {"min_intervall": 1}}
        with self.assertRaisesRegex(config.ConfigError, "min_intervall"):
            runtime.policies_from_config(cfg)

    def test_user_agent_is_generic_unless_researcher_adds_email(self):
        cfg = config.defaults()
        self.assertNotIn("mailto", runtime.user_agent(cfg))
        cfg["contact_email"] = "someone@example.org"
        self.assertIn("mailto:someone@example.org", runtime.user_agent(cfg))

    def test_bind_root(self):
        g = {"__file__": str(ROOT / "scripts" / "x.py"), "ROOT": ROOT, "RAW_DIR": ROOT / "results" / "raw"}
        self.assertFalse(runtime.bind_root(g, ROOT, {"RAW_DIR": "results/raw"}))   # 在仓库里运行：什么都不变
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(runtime.bind_root(g, d, {"RAW_DIR": "results/raw"}))
            self.assertEqual(g["RAW_DIR"], Path(d).resolve() / "results" / "raw")
            self.assertEqual(g["ROOT"], Path(d).resolve())

    def test_early_language(self):
        with tempfile.TemporaryDirectory() as d:
            write_cfg(d, {"language": "en"})
            self.assertEqual(i18n.early_language(["--lang", "zh"], {"NP_LANG": "en"}), "zh")
            self.assertEqual(i18n.early_language(["--lang=en"], {}), "en")
            self.assertEqual(i18n.early_language([], {"NP_LANG": "en"}), "en")
            self.assertEqual(i18n.early_language(["--root", d], {}), "en")      # 配置文件里的 language
            self.assertEqual(i18n.early_language(["--root", d], {"NP_LANG": "zh"}), "zh")

    def test_message_table_is_complete(self):
        for key, entry in i18n.MESSAGES.items():
            self.assertEqual(set(entry), {"zh", "en"}, key)
            self.assertTrue(all(entry.values()), key)


class TestConfigReachesScripts(LanguageReset):
    def test_version_rules_from_config(self):
        cfg = config.defaults()
        cfg["versions"]["preprint_doi_prefixes"] = cfg["versions"]["preprint_doi_prefixes"] + ["10.9999/"]
        cfg["versions"]["year_window"] = 1
        rules = textmatch.VersionRules.from_config(cfg)
        self.assertTrue(rules.is_preprint_doi("10.9999/abc"))
        self.assertFalse(textmatch.DEFAULT_RULES.is_preprint_doi("10.9999/abc"))
        title = "A long enough title about generative AI in science"
        a = textmatch.version_summary([{"title": title, "year": 2020, "doi": "10.1/a"}], rules=rules)
        b = textmatch.version_summary([{"title": title, "year": 2022, "doi": None}], rules=rules)
        self.assertEqual(textmatch.version_decision(a, b, rules=rules)[0], "review")      # 相差 2 年 > 1
        self.assertEqual(textmatch.version_decision(a, b)[0], "merge")                    # 默认窗口 3 年
        self.assertEqual(textmatch.VersionRules(preprint_doi_prefixes=[]).preprint_doi.match("10.1/x"), None)

    def test_search_truncation_and_purposes_from_config(self):
        cfg = config.defaults()
        cfg["queries"]["truncation"]["theor*"] = "theory"
        cfg["queries"]["purposes"]["concurrent"]["year_from"] = 2024
        try:
            with self.assertRaisesRegex(ValueError, "theor"):
                search.to_openalex("theor* AND science")
            search.configure(cfg)
            self.assertEqual(search.to_openalex("theor* AND science"), "theory AND science")
            self.assertEqual(search.YEAR_FROM["concurrent"], 2024)
        finally:
            search.configure(config.defaults())
        with self.assertRaisesRegex(ValueError, "theor"):
            search.to_openalex("theor* AND science")                                     # 每次调用整体替换，不累加

    def test_english_messages(self):
        i18n.set_language("en")
        with self.assertRaisesRegex(ValueError, "Nested parentheses"):
            search.parse_query("(a OR (b))")
        with self.assertRaisesRegex(ValueError, "Operators must be upper case"):
            search.parse_query("a and b")
        i18n.set_language("zh")
        with self.assertRaisesRegex(ValueError, "不支持嵌套括号"):
            search.parse_query("(a OR (b))")

    def test_merge_reads_config_from_another_project_root(self):
        """--root 指向另一个项目目录，--config 改 top_k：候选表的条数随之变化，meta 记下参数与 config_hash。"""
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "results" / "raw"
            raw.mkdir(parents=True)
            for f in (EXAMPLE / "results" / "raw").glob("*_v2.json"):
                shutil.copy(f, raw / f.name)
            (Path(d) / "PROJECT.md").write_text("marker\n", encoding="utf-8")
            cfg_file = write_cfg(d, {"merge": {"top_k": 5}})
            argv = ["merge.py", "--root", d, "--suffix", "_v2", "--config", str(cfg_file)]
            try:
                with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(_io.StringIO()):
                    self.assertEqual(merge.main(), 0)
            finally:
                merge.configure(config.defaults())
                for name, value in (("ROOT", ROOT), ("RAW_DIR", ROOT / "results" / "raw"),
                                    ("OUT_DIR", ROOT / "results" / "merged")):
                    setattr(merge, name, value)
            out = json.loads((Path(d) / "results" / "merged" / "merged_v2.json").read_text(encoding="utf-8"))
            rows = (Path(d) / "results" / "merged" / "candidates_v2.csv").read_text(encoding="utf-8-sig").splitlines()
        self.assertEqual(out["meta"]["parameters"]["top_k"], 5)
        self.assertEqual(out["meta"]["config_file"], config.CONFIG_NAME)
        self.assertEqual(len(out["meta"]["config_hash"]), 12)
        self.assertEqual(len(rows), 1 + 5)


class TestEnglishCommandLine(unittest.TestCase):
    """子进程里用 NP_LANG=en / --lang en 运行：帮助文本与检查结果都是英文。"""

    def run_search(self, *args, env=None):
        import subprocess
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "search.py"), *args], capture_output=True,
                              text=True, encoding="utf-8", env={**CHILD_ENV, **(env or {})})

    def test_help_and_dry_run(self):
        q = str(EXAMPLE / "queries" / "queries.json")
        en = self.run_search("--help", env={"NP_LANG": "en"})
        self.assertIn("Run only these queries", en.stdout)
        self.assertIn("Interface language", en.stdout)
        zh = self.run_search("--help")
        self.assertIn("只跑这些检索式", zh.stdout)
        r = self.run_search("--dry-run", "--queries", q, "--lang", "en")
        self.assertEqual(r.returncode, 0)
        self.assertIn("6/6 queries valid (dry run, nothing sent)", r.stdout)
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "q.json"
            bad.write_text(json.dumps([{"id": "Q1", "query": "a and b", "purpose": "component"},
                                       {"id": "X", "query": "a", "purpose": "other"}]), encoding="utf-8")
            r = self.run_search("--dry-run", "--queries", str(bad), "--lang", "en")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Problems in the queries file", r.stdout)
        self.assertIn("item 2: id 'X' must look like Q1, Q2", r.stdout)


class TestConfigCommand(unittest.TestCase):
    def run_config(self, *args, cwd=None):
        import subprocess
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "config.py"), *args], capture_output=True,
                              text=True, encoding="utf-8", env=CHILD_ENV, cwd=cwd)

    def test_init_check_show(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "PROJECT.md").write_text("marker\n", encoding="utf-8")
            self.assertEqual(self.run_config("init", "--root", d).returncode, 0)
            self.assertEqual(self.run_config("init", "--root", d).returncode, 1)        # 不覆盖已有文件
            self.assertEqual(self.run_config("check", "--root", d).returncode, 0)
            shown = self.run_config("show", "--diff", "--root", d)
            self.assertEqual(json.loads(shown.stdout), {})
            write_cfg(d, {"merge": {"top_k": "x"}})
            r = self.run_config("check", "--root", d, "--lang", "en")
            self.assertEqual(r.returncode, 2)
            self.assertIn("merge.top_k must be a positive integer", r.stderr)


if __name__ == "__main__":
    unittest.main()
