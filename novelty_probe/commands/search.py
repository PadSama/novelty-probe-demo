#!/usr/bin/env python3
"""novelty-probe 检索脚本。

对 queries/queries.json 中的每条检索式，分别查询配置中启用的数据源（novelty_probe/sources/，默认 OpenAlex 与
Semantic Scholar；Crossref 默认关闭），各取前 25 条，原样存到 results/raw/{source}_{query_id}{suffix}.json
（suffix 默认为空；v2 用 --queries queries/queries_v2.json --suffix _v2），并在终端打印命中数。

输出文件结构：{"meta": {...}, "records": [...]}
  meta    实际发送的检索串、请求地址、排序方式、API 报告的总命中数、检索时间、所用配置等。
  records 每条只有 title, year, doi, arxiv_id, venue, abstract, source_api, query_id（本地重排的来源另有 local_rank），
          按排序后的顺序保存，不去重。值直接取自 API 返回，只做格式整理：
          DOI 去掉 https://doi.org/ 前缀；arXiv ID 去掉版本号；OpenAlex 摘要由倒排索引还原；Crossref 摘要去掉 JATS 标签；
          OpenAlex 没有 arXiv 字段，arxiv_id 取自 arXiv DOI（10.48550/arXiv.*）或 arxiv.org 链接。

检索式先解析为语法树（novelty_probe/query.py，写法见 AGENTS.md；错误带错误码与位置，dry-run 用 ^ 标出），
各数据源从同一棵语法树序列化（以下行为均实测）：
  OpenAlex          filter=title_and_abstract.search，照原文发送，按 relevance_score 降序取前 25 条；截断词换成完整词
                    （配置 queries.truncation）；保存前核对 OpenAlex 返回的解析结果（运算符被当成词、NOT 丢失、分组不同都报错）。
  Semantic Scholar  bulk 接口，AND 换成 +，OR 换成 |，AND NOT 换成 + -；按被引次数取回全部命中（最多 max_records 条）后本地重排。
  Crossref          （默认关闭）词袋检索，布尔、短语与排除在本地实现，有损处写进 meta.lossy；本地重排。
  purpose 为 concurrent 的检索式只取 2023 年起的文献（配置 queries.purposes.concurrent.year_from）。
加一个数据源只需在 novelty_probe/sources/ 写一个模块并登记，本脚本不用改。

参数来自配置 novelty-probe.json（novelty_probe/config.py）：sources.<来源>.enabled / top_n / max_records、
  queries.purposes.<用途>.year_from、queries.truncation；每个输出文件的 meta.config_hash 记录所用配置。
  通用参数 --root / --config / --lang（novelty_probe/runtime.py）。
请求估算：dry-run 与正式运行开头都打印各来源最多发多少请求、OpenAlex 最多花多少额度；运行中 OpenAlex 剩余额度不够完成余下的
  请求时提前警告。
HTTP 层（novelty_probe/http.py）：按主机限速、重试、缓存与录制回放，命令行 --http-mode / --cache-dir / --cassette / --refresh；
  每个输出文件的 meta.http 记录请求数、缓存命中、重试、OpenAlex 额度头；meta.warnings 记录响应形状与解析核对的警告。
可选环境变量（不会写进输出文件）：
  OPENALEX_API_KEY  本云环境中 key 已由 Network secrets 在代理层注入，无需设置；在本机运行时才需要。
  S2_API_KEY        不设也能运行，但匿名请求共用限流池，容易返回 429。有 key 时的限额是每秒 1 个请求、所有接口合计，
                    客户端对发往 api.semanticscholar.org 的每个请求（含翻页与重试）统一节流。不要同时运行两个会访问 S2 的脚本。

用法：
  novelty-probe search                                  # 全部检索式 × 启用的来源
  novelty-probe search --ids Q1,Q3 --sources semanticscholar
  novelty-probe search --queries queries/queries_v2.json --suffix _v2
  novelty-probe search --dry-run                        # 不联网，只检查检索式语法并打印各来源的检索串与请求估算
"""
import argparse
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from novelty_probe.paths import PACKAGE_ROOT
from novelty_probe import config as np_config, i18n, runtime, sources
from novelty_probe import query as Q
from novelty_probe.http import default_client
from novelty_probe.i18n import t
from novelty_probe.paths import rel
from novelty_probe.io import load_json_lenient, write_json
# 以下名字原来定义在本脚本里，阶段 3 移入 novelty_probe/sources/；保留在这里，供其他脚本与测试照旧使用
from novelty_probe.sources.common import clean_arxiv, clean_doi, rebuild_abstract  # noqa: F401
from novelty_probe.sources.localrank import local_rank
from novelty_probe.sources.openalex import check_interpretation as _check_openalex
from novelty_probe.sources.openalex import openalex_arxiv, openalex_record  # noqa: F401
from novelty_probe.sources.semanticscholar import s2_record  # noqa: F401
from novelty_probe.sources import openalex as _oa, semanticscholar as _s2

ROOT = PACKAGE_ROOT   # 源码仓库（在仓库里运行时）；其他项目目录由 runtime.bind_root 换成该目录
QUERIES_FILE = ROOT / "queries" / "queries.json"
RAW_DIR = ROOT / "results" / "raw"

TOP_N = 25               # 默认；配置 sources.<来源>.top_n
OPENALEX_URL = _oa.URL
OPENALEX_SORT = _oa.SORT
S2_URL = _s2.URL
S2_FIELDS = _s2.FIELDS
S2_SORT = _s2.SORT
S2_MAX_RECORDS = _s2.SemanticScholar.default_max_records   # 配置 sources.semanticscholar.max_records
# 限速、重试、Retry-After 上限等见 novelty_probe/http.py 的 POLICIES（S2：每秒 1 个请求，所有接口合计）

# 以下两项由 configure(cfg) 按配置设定（queries.truncation / purposes），这里是内置默认值。
# 截断词 → 完整词（OpenAlex、Crossref 不支持通配符）。遇到未登记的截断词就报错（Q201），避免悄悄改变检索含义。
TRUNCATION = dict(np_config.DEFAULTS["queries"]["truncation"])
# purpose → 起始年份（None 表示不限）
YEAR_FROM = {k: v.get("year_from") for k, v in np_config.DEFAULTS["queries"]["purposes"].items()}
PURPOSES = set(YEAR_FROM)
ID_RE = re.compile(r"^Q\d+$")  # merge.py 只读取 {source}_Q<数字>{suffix}.json，id 必须是这种格式（文件名约定，不可配置）


def configure(cfg):
    """按配置设定截断词表、purpose 及其起始年份（main() 开头调用；snowball.py 也调用）。每次调用整体替换，不累加。"""
    global TRUNCATION, YEAR_FROM, PURPOSES
    q = cfg["queries"]
    TRUNCATION = dict(q["truncation"])
    YEAR_FROM = {k: (v or {}).get("year_from") for k, v in q["purposes"].items()}
    PURPOSES = set(YEAR_FROM)


# ---------- 检索式（解析与序列化在 novelty_probe/query.py 与 novelty_probe/sources/） ----------

def parse_query(query):
    """'A AND (B OR C) AND NOT (D OR E)' → ([['A'], ['B', 'C']], [['D', 'E']])，即（包含组，排除组）；不合写法时抛 QueryError。"""
    return Q.parse(query).lists()


def and_groups(query):
    """检索式的包含组（排除组见 parse_query）。"""
    return parse_query(query)[0]


def expand_truncation(text):
    return _oa.expand_truncation(text, TRUNCATION)


def to_openalex(query):
    """通用布尔式 → OpenAlex：照原样发送，截断词换成完整词。"""
    return sources.REGISTRY["openalex"].serialize(Q.parse(query), TRUNCATION)


def to_s2_bulk(query):
    """通用布尔式 → S2 bulk 语法：AND → +，OR → |，AND NOT (…) → + -(…)；括号、引号短语、截断词原样保留。"""
    return sources.REGISTRY["semanticscholar"].serialize(Q.parse(query), TRUNCATION)


# ---------- HTTP ----------

def get_json(url, headers=None, retries=None):
    """GET 并解析 JSON，经由 novelty_probe.http 的统一客户端（缓存、按主机限速、重试、错误分类；密钥由客户端按主机加上）。
    各数据源经由这个函数取数（测试可替换）；retries 参数已由客户端策略决定，忽略。"""
    return default_client().get_json(url, headers=headers)


def check_openalex_interpretation(query_sent, api_meta):
    return _check_openalex(query_sent, api_meta)


def context(top_n=None, max_records=0, checkpoint=None):
    """数据源的运行环境：取数经由本模块的 get_json（调用时再取，测试替换后同样生效）。"""
    return sources.Context(fetch=lambda url: get_json(url), client=default_client(), truncation=TRUNCATION,
                           top_n=TOP_N if top_n is None else top_n, max_records=max_records, checkpoint=checkpoint)


# ---------- 各来源（兼容旧接口） ----------

def search_openalex(q, year_from, top_n=None):
    return sources.REGISTRY["openalex"].search(q, year_from, context(top_n))


def s2_local_rank(papers, query, top_n=None):
    return local_rank(papers, query, TOP_N if top_n is None else top_n, _s2.citations)


def search_s2(q, year_from, checkpoint=None, top_n=None, max_records=None):
    return sources.REGISTRY["semanticscholar"].search(
        q, year_from, context(top_n, S2_MAX_RECORDS if max_records is None else max_records, checkpoint))


def load_queries(path):
    """读取并校验检索式文件（结构：id、query、purpose）；有问题时抛出 ValueError，列出所有问题。检索式语法由 dry-run 检查。"""
    queries = load_json_lenient(path)  # 容忍 BOM 与 ```json 围栏
    if not isinstance(queries, list) or not queries:
        raise ValueError(t("queries.not_array", path=path))
    problems, seen = [], set()
    for i, q in enumerate(queries, 1):
        if not isinstance(q, dict):
            problems.append(t("queries.not_object", i=i))
            continue
        qid = q.get("id")
        who = qid if isinstance(qid, str) and qid else t("queries.item", i=i)
        if not isinstance(qid, str) or not ID_RE.match(qid):
            problems.append(t("queries.bad_id", i=i, qid=repr(qid), pattern=ID_RE.pattern))
        elif qid in seen:
            problems.append(t("queries.duplicate_id", qid=qid))
        seen.add(qid)
        if not isinstance(q.get("query"), str) or not q["query"].strip():
            problems.append(t("queries.missing_query", who=who))
        if q.get("purpose") not in PURPOSES:
            problems.append(t("queries.bad_purpose", who=who, purpose=repr(q.get("purpose")), allowed="/".join(sorted(PURPOSES))))
    if problems:
        raise ValueError(t("queries.problems") + "\n  " + "\n  ".join(problems))
    return queries


# ---------- 主流程 ----------

def enabled_sources(cfg):
    """配置中启用的来源（按注册表顺序）；配置里写了本版本不认识的来源时给出警告。"""
    for name in (cfg.get("sources") or {}):
        if name not in sources.REGISTRY:
            print(i18n.tr("配置警告：本版本不支持来源 {name}，已忽略", "config warning: source {name} is not supported by this version; ignored",
                          name=name), file=sys.stderr)
    return sources.enabled(cfg)


def source_settings(cfg, name):
    """某来源的 top_n 与 max_records（配置 sources.<name>）。"""
    s = (cfg.get("sources") or {}).get(name) or {}
    src = sources.REGISTRY[name]
    return s.get("top_n", TOP_N), s.get("max_records") or src.default_max_records


def request_plan(cfg, names, n_queries):
    """各来源最多发多少个请求、OpenAlex 最多花多少额度（上限：翻页的来源按 max_records 计）。"""
    plan = {}
    for name in names:
        top_n, max_records = source_settings(cfg, name)
        p = sources.REGISTRY[name].plan(top_n, max_records)
        plan[name] = {"requests": p["requests"] * n_queries, "credits": p["credits_per_request"] * p["requests"] * n_queries}
    return plan


def plan_line(plan):
    parts = []
    for name, p in plan.items():
        part = t("search.plan_source", name=name, n=p["requests"])
        if p["credits"]:
            part += t("search.plan_credits", credits=p["credits"])
        parts.append(part)
    return t("search.plan", lines=t("verify.sep").join(parts))


def hyphen_hint(parsed):
    terms = [term.raw for term in parsed.terms() + parsed.terms(negated=True) if term.kind != "phrase" and "-" in term.raw]
    return t("search.hyphen_hint", terms=", ".join(terms)) if terms else None


def dry_run(queries, names):
    bad = 0
    for q in queries:
        try:
            parsed = Q.parse(q["query"])
            lines = []
            for name in names:
                src = sources.REGISTRY[name]
                skip = src.unsupported(parsed)
                text = t("search.skipped", reason="; ".join(skip)) if skip else src.serialize(parsed, TRUNCATION)
                lines.append(f"  {name + ':':<17}{text}")
        except Q.QueryError as e:
            bad += 1
            print(f"{q['id']} INVALID: {e}\n  query: {q['query']}")
            if e.pos is not None:
                print("         " + Q.caret(q["query"], e.pos))
            continue
        print(f"{q['id']} [{q['purpose']}]\n" + "\n".join(lines))
        hint = hyphen_hint(parsed)
        if hint:
            print("  " + hint)
    return bad


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Run queries/queries.json against the enabled sources (OpenAlex, Semantic Scholar; Crossref optional).")
    ap.add_argument("--ids", help=t("search.arg.ids"))
    ap.add_argument("--sources", default=None, help=t("search.arg.sources"))
    ap.add_argument("--queries", type=Path, default=None, help=t("search.arg.queries"))
    ap.add_argument("--suffix", default="", help=t("arg.suffix_out"))
    ap.add_argument("--dry-run", action="store_true", help=t("search.arg.dry_run"))
    runtime.add_common_args(ap, network=True)
    args = ap.parse_args()
    rt = runtime.init(args)
    runtime.bind_root(globals(), rt.root, {"QUERIES_FILE": "queries/queries.json", "RAW_DIR": "results/raw"})
    cfg, client = rt.cfg, rt.client
    configure(cfg)

    queries_path = args.queries or QUERIES_FILE
    try:
        queries = load_queries(queries_path)
    except (OSError, ValueError) as e:
        print(e)
        return 2
    qfile = rel(queries_path, ROOT)
    if args.ids:
        wanted = set(args.ids.split(","))
        missing = wanted - {q["id"] for q in queries}
        if missing:
            ap.error(t("search.unknown_ids", ids=", ".join(sorted(missing))))
        queries = [q for q in queries if q["id"] in wanted]
    names = args.sources.split(",") if args.sources else enabled_sources(cfg)
    unknown = set(names) - set(sources.REGISTRY)
    if unknown:
        ap.error(t("search.unknown_sources", names=", ".join(sorted(unknown))))
    plan = request_plan(cfg, names, len(queries))
    if args.dry_run:
        bad = dry_run(queries, names)
        print("\n" + t("search.dry_summary", ok=len(queries) - bad, total=len(queries)))
        print(plan_line(plan))
        return 1 if bad else 0
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(plan_line(plan))

    def row(*cells):
        print("{:<5} {:<11} {:<15} {:>10} {:>5} {:>5}  {}".format(*map(str, cells)))

    row("query", "purpose", "source", "total_hits", "saved", "no_id", "file / note")
    failed, warned = 0, False
    oa_left = len(queries) if "openalex" in names else 0
    cfg_meta = np_config.meta(cfg, lambda f: rel(f, ROOT))
    for q in queries:
        year_from = YEAR_FROM.get(q["purpose"])
        for name in names:
            src = sources.REGISTRY[name]
            top_n, max_records = source_settings(cfg, name)
            if name == "openalex":
                remaining = (client.stats.get("api.openalex.org") or {}).get("remaining")
                need = oa_left * plan[name]["credits"] // max(1, plan[name]["requests"])
                if not warned and remaining is not None and str(remaining).isdigit() and int(remaining) < need:
                    print("      " + t("search.credit_warning", remaining=remaining, n=oa_left, need=need))
                    warned = True
                oa_left -= 1
            try:
                Q.parse(q["query"])
                skip = src.unsupported(Q.parse(q["query"]))
                if skip:
                    row(q["id"], q["purpose"], name, "-", "-", "-", t("search.skipped", reason="; ".join(skip)))
                    continue
                ck = RAW_DIR / ".checkpoints" / f"{name}_{q['id']}{args.suffix}.json" if src.paginates else None
                meta, records = src.search(q, year_from, context(top_n, max_records, ck))
            except Exception as e:  # 单个请求失败不影响其他请求
                failed += 1
                row(q["id"], q["purpose"], name, "-", "-", "-", f"FAILED: {e}")
                continue
            for w in meta.get("warnings") or []:
                print(f"      warning [{q['id']} {name}]: {w}")
            meta = {"source_api": name, "query_id": q["id"], "purpose": q["purpose"],
                    "queries_file": qfile,
                    "query_original": q["query"], "year_from": year_from, "top_n": top_n, **meta,
                    "returned": len(records), "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    **cfg_meta, "http": client.stats_summary()}
            path = RAW_DIR / f"{name}_{q['id']}{args.suffix}.json"
            write_json(path, {"meta": meta, "records": records})
            no_id = sum(1 for r in records if not r["doi"] and not r["arxiv_id"])
            note = rel(path, ROOT)
            if year_from:
                note += f"  [year>={year_from}]"
            row(q["id"], q["purpose"], name, meta["total_hits"], len(records), no_id, note)

    total = len(queries) * len(names)
    top = sorted({source_settings(cfg, n)[0] for n in names})
    print("\n" + t("search.summary", ok=total - failed, total=total, top_n="/".join(map(str, top))))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
