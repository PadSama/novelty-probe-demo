"""项目配置：novelty-probe.json（JSON，Python 3.9 起可用；TOML 要 3.11）。

查找顺序：命令行 --config > 环境变量 NOVELTY_PROBE_CONFIG > 项目根目录下的 novelty-probe.json > 只用内置默认值。
合并规则：
- 用户文件里的对象与默认值逐层合并；列表整体替换；
- 以 _extend 结尾的键把列表追加到同名键的默认列表上（如 versions.preprint_doi_prefixes_extend）；
- 以 _ 开头的键视为注释，忽略；
- 未知的键给出警告（向前兼容），不报错；取值不合法时报 ConfigError，一次列出所有问题。
方法本身（Porter 词干还原、BM25 与 RRF 公式、版本识别规则的顺序、DOI/arXiv 正则、AND NOT 必须大写）不在配置里：
它们变了，结果就不可比。配置里放的是参数与词表。
config_hash：有效配置（去掉 contact_email 与 language：两者不影响检索与排序结果）的 sha256 前 12 位，
写进每个输出文件的 meta，便于核对两次运行是否同一配置。
"""
import copy
import hashlib
import json
import os
import re
from pathlib import Path

from . import defaults as D
from .i18n import tr
from .io import load_json_lenient

CONFIG_NAME = "novelty-probe.json"
SCHEMA = "novelty-probe/config@1"

DEFAULTS = {
    "schema": SCHEMA,
    "language": "zh",
    # 研究者自己决定是否填写；填写后加进 User-Agent 与 Crossref 的 mailto（礼貌池）。助手不代填。
    "contact_email": "",
    "facets": D.FACETS,
    "labels": D.LABELS,
    "columns": D.COLUMNS,
    "queries": {
        # purpose → 起始年份（null 表示不限）；可以增加新的 purpose。检索式 id 的格式（Q1、Q2…）是脚本之间的文件名约定，不在配置里
        "purposes": {
            "component": {"year_from": None},
            "application": {"year_from": None},
            "method": {"year_from": None},
            "concurrent": {"year_from": 2023},
        },
        # 截断词 → 完整词（OpenAlex 的默认检索不支持通配符）；未登记的截断词会报错
        "truncation": {
            "bibliometric*": "bibliometrics",
            "economist*": "economists",
            "scientist*": "scientists",
            "homogeniz*": "homogenization",
            "homogenis*": "homogenisation",
        },
    },
    "sources": {
        "openalex": {"enabled": True, "top_n": 25},
        "semanticscholar": {"enabled": True, "top_n": 25, "max_records": 3000},
        # 词袋检索、布尔在本地实现（有损，见 novelty_probe/sources/crossref.py）；默认关闭
        "crossref": {"enabled": False, "top_n": 25, "max_records": 1000},
    },
    "merge": {"top_k": 20, "rrf_k": 60, "bm25": {"k1": 1.2, "b": 0.75}},
    "versions": {
        "year_window": D.YEAR_WINDOW,
        "min_title_words": D.MIN_TITLE_WORDS,
        "preprint_doi_prefixes": D.PREPRINT_DOI_PREFIXES,
        "preprint_venues": D.PREPRINT_VENUES,
        "data_doi_prefixes": D.DATA_DOI_PREFIXES,
    },
    # 内容相似度（snowball.py）去掉的停用词；要追加时写 "stopwords_extend": [...]
    "textmatch": {"stopwords": D.STOPWORDS},
    "enrich": {"top": 20},
    "snowball": {"min_overlap": 2, "max_forward": 2000, "top": 20, "keep": 200},
    "compare": {
        "default_markers": "genai",
        # 标记词组：compare.py 统计前 K 篇中含这些词的篇数（默认 genai = 研究者在 Step 2 确定的筛选词）
        "marker_terms": {
            "genai": ["LLM", "LLMs", "ChatGPT", "GPT", "Gemini", "Claude", "OpenAI", "Anthropic", '"generative AI"',
                      '"generative artificial intelligence"', '"large language model"'],
        },
    },
    "verify": {"landing": True},
    "http": {
        # 按主机覆盖 novelty_probe/http.py 的 POLICIES，例如 {"api.semanticscholar.org": {"min_interval_s": 2.0}}
        "policies": {},
    },
}

_EXTEND = "_extend"


class ConfigError(ValueError):
    pass


class Config(dict):
    """有效配置（dict），另带 file（来源文件或 None）、warnings（未知键等）与 hash。"""

    file = None
    warnings = ()
    hash = ""

    def get_path(self, dotted, default=None):
        cur = self
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur


def _merge(base, user, path, warnings):
    for key, val in user.items():
        if key.startswith("_"):
            continue
        here = f"{path}.{key}" if path else key
        if key.endswith(_EXTEND):
            target = key[: -len(_EXTEND)]
            if isinstance(base.get(target), list) and isinstance(val, list):
                base[target] = list(base[target]) + [v for v in val if v not in base[target]]
            elif target in base:
                warnings.append(tr("{here}：{target} 不是列表，无法追加", "{here}: {target} is not a list; cannot extend",
                                   here=here, target=target))
            else:
                warnings.append(tr("{here}：未知的键 {target}", "{here}: unknown key {target}", here=here, target=target))
            continue
        if key not in base and path not in _OPEN_MAPS:
            warnings.append(tr("未知的配置键 {here}（已保留，但当前版本不使用）", "unknown config key {here} (kept, but unused by this version)",
                               here=here))
            base[key] = val
            continue
        if isinstance(base.get(key), dict) and isinstance(val, dict):
            _merge(base[key], val, here, warnings)
        else:
            base[key] = val


# 这些对象的键由用户自定义（不是固定的配置项）：新键不报"未知"，与默认值取并集
_OPEN_MAPS = {"queries.purposes", "queries.truncation", "compare.marker_terms", "http.policies", "sources"}


def _validate(cfg):
    problems = []

    def need(cond, zh, en, **kw):
        if not cond:
            problems.append(tr(zh, en, **kw))

    lang = cfg.get("language")
    need(cfg.get("schema") == SCHEMA, "schema 应为 {s!r}", "schema must be {s!r}", s=SCHEMA)
    need(lang in ("zh", "en"), "language 应为 zh 或 en", "language must be zh or en")
    need(isinstance(cfg.get("contact_email"), str), "contact_email 应为字符串（可为空）", "contact_email must be a string (may be empty)")
    facets = cfg.get("facets")
    if not (isinstance(facets, list) and 1 <= len(facets) <= 12):
        need(False, "facets 应为 1–12 个对象的列表", "facets must be a list of 1–12 objects")
    else:
        keys = [f.get("key") if isinstance(f, dict) else None for f in facets]
        for i, f in enumerate(facets):
            if not isinstance(f, dict) or not isinstance(f.get("key"), str) or not re.match(r"^[a-z][a-z0-9_]*$", f["key"]):
                need(False, "facets[{i}].key 应由小写字母、数字、下划线组成", "facets[{i}].key must use lowercase letters, digits, underscores", i=i)
            elif not isinstance(f.get("label"), dict) or not all(isinstance(v, str) and v for v in f["label"].values()):
                need(False, "facets[{i}].label 应为 {{语言: 标签}} 对象", "facets[{i}].label must be a {{language: label}} object", i=i)
            elif lang not in f["label"]:
                need(False, "facets[{i}] 缺少当前语言 {lang} 的标签", "facets[{i}] has no label for the current language {lang}", i=i, lang=lang)
        need(len(set(keys)) == len(keys), "facets 的 key 不能重复", "facet keys must be unique")
    need(isinstance(cfg.get("labels"), list) and all(isinstance(x, str) and x for x in cfg["labels"]) and "overlap" in cfg["labels"],
         "labels 应为字符串列表，且包含 overlap（snowball.py 按它挑选种子）",
         "labels must be a list of strings that includes overlap (snowball.py picks seeds by it)")
    cols = cfg.get("columns")
    need(isinstance(cols, dict) and all(isinstance(v, list) and v for v in cols.values()) and
         {"rank", "title", "id", "verified"} <= set(cols or {}),
         "columns 应包含 rank / title / id / verified 的别名列表", "columns must hold alias lists for rank / title / id / verified")
    q = cfg.get("queries") or {}
    purposes = q.get("purposes")
    if not (isinstance(purposes, dict) and purposes):
        need(False, "queries.purposes 应为非空对象", "queries.purposes must be a non-empty object")
    else:
        for name, pv in purposes.items():
            yf = pv.get("year_from") if isinstance(pv, dict) else "?"
            need(yf is None or (isinstance(yf, int) and 1900 <= yf <= 2100),
                 "queries.purposes.{name}.year_from 应为年份或 null", "queries.purposes.{name}.year_from must be a year or null", name=name)
    trunc = q.get("truncation")
    if not isinstance(trunc, dict):
        need(False, "queries.truncation 应为对象", "queries.truncation must be an object")
    else:
        for k, v in trunc.items():
            need(isinstance(k, str) and k.endswith("*") and len(k) > 1 and isinstance(v, str) and v and "*" not in v,
                 "queries.truncation 的条目 {k!r}: {v!r} 不合法（键以 * 结尾，值是完整词）",
                 "queries.truncation entry {k!r}: {v!r} is invalid (key ends with *, value is the full word)", k=k, v=v)
    for name, src in (cfg.get("sources") or {}).items():
        if not isinstance(src, dict):
            need(False, "sources.{name} 应为对象", "sources.{name} must be an object", name=name)
            continue
        need(isinstance(src.get("enabled", True), bool), "sources.{name}.enabled 应为 true / false", "sources.{name}.enabled must be true / false", name=name)
        tn = src.get("top_n", 25)
        need(isinstance(tn, int) and 1 <= tn <= 200, "sources.{name}.top_n 应为 1–200 的整数（OpenAlex 每页最多 200）",
             "sources.{name}.top_n must be an integer 1–200 (OpenAlex returns at most 200 per page)", name=name)
        if "max_records" in src:
            mr = src["max_records"]
            need(isinstance(mr, int) and 1 <= mr <= 10000, "sources.{name}.max_records 应为 1–10000 的整数",
                 "sources.{name}.max_records must be an integer 1–10000", name=name)
    m = cfg.get("merge") or {}
    need(isinstance(m.get("top_k"), int) and m["top_k"] >= 1, "merge.top_k 应为正整数", "merge.top_k must be a positive integer")
    need(isinstance(m.get("rrf_k"), (int, float)) and m["rrf_k"] > 0, "merge.rrf_k 应为正数", "merge.rrf_k must be positive")
    bm = m.get("bm25") or {}
    need(isinstance(bm.get("k1"), (int, float)) and bm["k1"] >= 0, "merge.bm25.k1 应为非负数", "merge.bm25.k1 must be non-negative")
    need(isinstance(bm.get("b"), (int, float)) and 0 <= bm["b"] <= 1, "merge.bm25.b 应在 0–1 之间", "merge.bm25.b must be between 0 and 1")
    v = cfg.get("versions") or {}
    need(isinstance(v.get("year_window"), int) and v["year_window"] >= 0, "versions.year_window 应为非负整数",
         "versions.year_window must be a non-negative integer")
    need(isinstance(v.get("min_title_words"), int) and v["min_title_words"] >= 1, "versions.min_title_words 应为正整数",
         "versions.min_title_words must be a positive integer")
    for k in ("preprint_doi_prefixes", "preprint_venues", "data_doi_prefixes"):
        need(isinstance(v.get(k), list) and all(isinstance(x, str) and x for x in v[k]),
             "versions.{k} 应为字符串列表", "versions.{k} must be a list of strings", k=k)
    for k in ("min_overlap", "max_forward", "top", "keep"):
        val = (cfg.get("snowball") or {}).get(k)
        need(isinstance(val, int) and val >= 1, "snowball.{k} 应为正整数", "snowball.{k} must be a positive integer", k=k)
    need(isinstance((cfg.get("enrich") or {}).get("top"), int), "enrich.top 应为整数", "enrich.top must be an integer")
    c = cfg.get("compare") or {}
    mt = c.get("marker_terms")
    need(isinstance(mt, dict) and all(isinstance(x, list) and all(isinstance(y, str) for y in x) for x in mt.values()),
         "compare.marker_terms 应为 {{名称: [检索词…]}}", "compare.marker_terms must be {{name: [terms…]}}")
    need(isinstance(mt, dict) and c.get("default_markers") in mt, "compare.default_markers 应为 marker_terms 中的一个名称",
         "compare.default_markers must name one of marker_terms")
    need(isinstance((cfg.get("verify") or {}).get("landing"), bool), "verify.landing 应为 true / false", "verify.landing must be true / false")
    pol = (cfg.get("http") or {}).get("policies")
    need(isinstance(pol, dict) and all(isinstance(x, dict) for x in pol.values()),
         "http.policies 应为 {{主机: {{参数: 值}}}}", "http.policies must be {{host: {{parameter: value}}}}")
    sw = (cfg.get("textmatch") or {}).get("stopwords")
    need(isinstance(sw, list) and all(isinstance(x, str) for x in sw), "textmatch.stopwords 应为字符串列表",
         "textmatch.stopwords must be a list of strings")
    if problems:
        raise ConfigError(tr("配置有问题：", "Problems in the config:") + "\n  " + "\n  ".join(problems))


_NOT_HASHED = ("contact_email", "language")


def config_hash(cfg):
    data = {k: v for k, v in cfg.items() if k not in _NOT_HASHED}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def find_config_file(explicit=None, root=None, env=None):
    env = os.environ if env is None else env
    if explicit:
        return Path(explicit)
    if env.get("NOVELTY_PROBE_CONFIG"):
        return Path(env["NOVELTY_PROBE_CONFIG"])
    if root is not None and (Path(root) / CONFIG_NAME).is_file():
        return Path(root) / CONFIG_NAME
    return None


def load_config(path=None, root=None, env=None):
    """返回 Config。path / root / env 见模块说明。指定的文件不存在时报 ConfigError。"""
    cfg = Config(copy.deepcopy(DEFAULTS))
    warnings = []
    file = find_config_file(path, root, env)
    if file is not None:
        if not file.is_file():
            raise ConfigError(tr("找不到配置文件 {f}", "Config file not found: {f}", f=file))
        try:
            user = load_json_lenient(file)
        except ValueError as e:
            raise ConfigError(str(e)) from None
        if not isinstance(user, dict):
            raise ConfigError(tr("{f} 应为 JSON 对象", "{f} must be a JSON object", f=file))
        _merge(cfg, user, "", warnings)
        cfg.file = file
    _validate(cfg)
    cfg.warnings = warnings
    cfg.hash = config_hash(cfg)
    return cfg


def defaults():
    """只含内置默认值的 Config（不读文件）。"""
    cfg = Config(copy.deepcopy(DEFAULTS))
    cfg.hash = config_hash(cfg)
    return cfg


def diff(cfg, base=None):
    """有效配置中与内置默认值不同的部分（嵌套对象逐层比较；列表整体比较）。"""
    base = DEFAULTS if base is None else base
    out = {}
    for k, v in cfg.items():
        if k not in base:
            out[k] = v
        elif isinstance(v, dict) and isinstance(base[k], dict):
            sub = diff(v, base[k])
            if sub:
                out[k] = sub
        elif v != base[k]:
            out[k] = v
    return out


STARTER = {
    "schema": SCHEMA,
    "_comment": "Only settings that differ from the built-in defaults go here. "
                "Show all settings with: python3 scripts/config.py show   |   "
                "这里只写与内置默认值不同的设置；查看全部设置：python3 scripts/config.py show",
    "language": "zh",
    "contact_email": "",
}


def meta(cfg, rel=str):
    """写进输出文件 meta 的配置信息。"""
    return {"config_file": rel(cfg.file) if cfg.file else None, "config_hash": cfg.hash}
