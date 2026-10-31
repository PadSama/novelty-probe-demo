#!/usr/bin/env python3
"""novelty-probe 检索脚本。

对 queries/queries.json 中的每条检索式，分别查询
  - OpenAlex          GET https://api.openalex.org/works?search=...
  - Semantic Scholar  GET https://api.semanticscholar.org/graph/v1/paper/search?query=...
各取前 25 条，原样存到 results/raw/{source}_{query_id}.json，并在终端打印命中数。

输出文件结构：{"meta": {...}, "records": [...]}
  meta    实际发送的检索串、请求地址、API 报告的总命中数、检索时间等。
  records 每条只有 title, year, doi, arxiv_id, venue, abstract, source_api, query_id，
          按 API 返回顺序保存，不去重、不筛选。值直接取自 API 返回，只做格式整理：
          DOI 去掉 https://doi.org/ 前缀；arXiv ID 去掉版本号；OpenAlex 摘要由倒排索引还原；
          OpenAlex 没有 arXiv 字段，arxiv_id 取自 arXiv DOI（10.48550/arXiv.*）或 arxiv.org 链接。

检索式转换（queries.json 是通用布尔写法）：
  OpenAlex          支持 AND / OR、括号和引号短语，照原样发送；截断词（*）换成完整词，
                    词形变化交给 OpenAlex 的词干还原。
  Semantic Scholar  该接口不支持任何检索语法，带连字符的词会零命中（见其 API 文档）。
                    先发送压平后的全部检索词（去掉运算符、括号、引号，连字符换空格）；
                    若零命中，再发送"每个 AND 组取第一个词"的核心词版本。两次尝试都记在 meta 里。
  purpose 为 concurrent 的检索式只取 2023 年起的文献（facets/facets.md 中的约定）。

可选环境变量（不设也能运行，且不会写进输出文件）：S2_API_KEY、OPENALEX_API_KEY、OPENALEX_MAILTO。

用法：
  python3 scripts/search.py                                  # 全部检索式 × 两个来源
  python3 scripts/search.py --ids Q1,Q3 --sources semanticscholar
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERIES_FILE = ROOT / "queries" / "queries.json"
RAW_DIR = ROOT / "results" / "raw"

TOP_N = 25
CONCURRENT_FROM_YEAR = 2023
USER_AGENT = "novelty-probe/0.1 (literature search script)"
OPENALEX_URL = "https://api.openalex.org/works"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,year,externalIds,venue,journal,abstract"
S2_PAUSE = 1.1  # 不带 API key 时 S2 限流较严，请求之间留间隔

# 截断词 → 完整词。遇到未登记的截断词就报错，避免悄悄改变检索含义。
TRUNCATION = {
    "bibliometric*": "bibliometrics",
    "scientist*": "scientists",
    "homogeniz*": "homogenization",
    "homogenis*": "homogenisation",
}

TOKEN_RE = re.compile(r'"[^"]*"|[()]|[^\s()"]+')
ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.I)
ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(.+?)(?:\.pdf)?(?:[?#].*)?$", re.I)


# ---------- 检索式转换 ----------

def expand_truncation(text):
    def repl(m):
        tok = m.group(0)
        if tok not in TRUNCATION:
            raise ValueError(f"未登记的截断词 {tok}，请在 TRUNCATION 中补充完整词")
        return TRUNCATION[tok]
    return re.sub(r"[A-Za-z][\w-]*\*", repl, text)


def and_groups(query):
    """'A AND (B OR C)' → [['A'], ['B', 'C']]。
    只支持当前检索式的写法：顶层用 AND 连接，括号内只用 OR，不嵌套、不用 NOT；其他写法直接报错。"""
    groups, cur, depth = [], [], 0
    for tok in TOKEN_RE.findall(query):
        if tok == "(":
            depth += 1
            if depth > 1:
                raise ValueError("不支持嵌套括号")
        elif tok == ")":
            depth -= 1
        elif tok == "AND":
            if depth:
                raise ValueError("不支持括号内的 AND")
            groups.append(cur)
            cur = []
        elif tok == "OR":
            if not depth:
                raise ValueError("不支持括号外的 OR")
        elif tok == "NOT":
            raise ValueError("不支持 NOT")
        else:
            cur.append(tok)
    groups.append(cur)
    if depth or not all(groups):
        raise ValueError("括号不配对或存在空的 AND 组")
    return groups


def plain(term):
    return expand_truncation(term.strip('"')).replace("-", " ")


def to_openalex(query):
    and_groups(query)  # 只做语法检查
    return expand_truncation(query)


def to_s2(query):
    """返回按尝试顺序排列的 [(转换方式, 检索串), ...]。"""
    groups = and_groups(query)
    all_terms = " ".join(plain(t) for g in groups for t in g)
    core_terms = " ".join(plain(g[0]) for g in groups)
    tries = [("plain text: all terms", all_terms)]
    if core_terms != all_terms:
        tries.append(("plain text: first term of each AND group (fallback)", core_terms))
    return tries


# ---------- HTTP ----------

def get_json(url, headers=None, retries=5):
    """GET 并解析 JSON。429、5xx、超时、连接被重置时指数退避重试；
    其他错误直接抛出（包括代理拒绝连接：那是网络策略问题，重试没有用）。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(retries + 1):
        wait = 2 ** (attempt + 1)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if (e.code == 429 or e.code >= 500) and attempt < retries:
                retry_after = e.headers.get("Retry-After", "")
                time.sleep(min(60, max(wait, int(retry_after) if retry_after.isdigit() else 0)))
                continue
            body = e.read(300).decode("utf-8", "replace").strip()
            raise RuntimeError(f"HTTP {e.code} {body}") from None
        except (TimeoutError, ConnectionResetError) as e:
            if attempt < retries:
                time.sleep(wait)
                continue
            raise RuntimeError(f"{type(e).__name__}: {e}") from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, ConnectionResetError)) and attempt < retries:
                time.sleep(wait)
                continue
            raise RuntimeError(f"network error: {e.reason}") from None


# ---------- 记录整理 ----------

def clean_doi(doi):
    if not doi:
        return None
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I) or None


def clean_arxiv(aid):
    if not aid:
        return None
    aid = re.sub(r"^arxiv:", "", aid.strip(), flags=re.I)
    return re.sub(r"v\d+$", "", aid) or None


def rebuild_abstract(inverted):
    if not inverted:
        return None
    words = sorted((pos, w) for w, positions in inverted.items() for pos in positions)
    return " ".join(w for _, w in words)


def openalex_arxiv(work, doi):
    m = ARXIV_DOI_RE.match(doi or "")
    if m:
        return clean_arxiv(m.group(1))
    for loc in work.get("locations") or []:
        for key in ("landing_page_url", "pdf_url"):
            m = ARXIV_URL_RE.search((loc or {}).get(key) or "")
            if m:
                return clean_arxiv(m.group(1))
    return None


def openalex_record(work, qid):
    doi = clean_doi(work.get("doi"))
    source = (work.get("primary_location") or {}).get("source") or {}
    return {
        "title": work.get("title") or work.get("display_name"),
        "year": work.get("publication_year"),
        "doi": doi,
        "arxiv_id": openalex_arxiv(work, doi),
        "venue": source.get("display_name"),
        "abstract": rebuild_abstract(work.get("abstract_inverted_index")),
        "source_api": "openalex",
        "query_id": qid,
    }


def s2_record(paper, qid):
    ext = paper.get("externalIds") or {}
    return {
        "title": paper.get("title"),
        "year": paper.get("year"),
        "doi": clean_doi(ext.get("DOI")),
        "arxiv_id": clean_arxiv(ext.get("ArXiv")),
        "venue": paper.get("venue") or (paper.get("journal") or {}).get("name") or None,
        "abstract": paper.get("abstract"),
        "source_api": "semanticscholar",
        "query_id": qid,
    }


# ---------- 两个来源 ----------

def search_openalex(q, year_from):
    params = {"search": to_openalex(q["query"]), "per-page": TOP_N, "page": 1}
    if year_from:
        params["filter"] = f"from_publication_date:{year_from}-01-01"
    secret = {k: v for k, v in (("api_key", os.environ.get("OPENALEX_API_KEY")),
                                 ("mailto", os.environ.get("OPENALEX_MAILTO"))) if v}
    data = get_json(f"{OPENALEX_URL}?{urllib.parse.urlencode({**params, **secret})}")
    time.sleep(0.2)
    records = [openalex_record(w, q["id"]) for w in (data.get("results") or [])[:TOP_N]]
    meta = {
        "conversion": "boolean kept; truncated words -> full words",
        "query_sent": params["search"],
        "request_url": f"{OPENALEX_URL}?{urllib.parse.urlencode(params)}",  # 不含 key / mailto
        "total_hits": (data.get("meta") or {}).get("count"),
    }
    return meta, records


def search_s2(q, year_from):
    key = os.environ.get("S2_API_KEY")
    headers = {"x-api-key": key} if key else {}
    attempts = []
    for conversion, text in to_s2(q["query"]):
        params = {"query": text, "offset": 0, "limit": TOP_N, "fields": S2_FIELDS}
        if year_from:
            params["year"] = f"{year_from}-"
        url = f"{S2_URL}?{urllib.parse.urlencode(params)}"
        data = get_json(url, headers)
        time.sleep(S2_PAUSE)
        attempts.append({"conversion": conversion, "query_sent": text,
                         "request_url": url, "total_hits": data.get("total", 0)})
        if data.get("total"):
            break
    records = [s2_record(p, q["id"]) for p in (data.get("data") or [])[:TOP_N]]
    return {**attempts[-1], "attempts": attempts}, records


SEARCHERS = {"openalex": search_openalex, "semanticscholar": search_s2}


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser(description="Run queries/queries.json against OpenAlex and Semantic Scholar.")
    ap.add_argument("--ids", help="只跑这些检索式，逗号分隔，如 Q1,Q3")
    ap.add_argument("--sources", default=",".join(SEARCHERS), help="逗号分隔：openalex,semanticscholar")
    args = ap.parse_args()

    queries = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    if args.ids:
        wanted = set(args.ids.split(","))
        queries = [q for q in queries if q["id"] in wanted]
    sources = args.sources.split(",")
    unknown = set(sources) - set(SEARCHERS)
    if unknown:
        ap.error(f"未知来源：{', '.join(sorted(unknown))}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    def row(*cells):
        print("{:<5} {:<11} {:<15} {:>10} {:>5} {:>5}  {}".format(*map(str, cells)))

    row("query", "purpose", "source", "total_hits", "saved", "no_id", "file / note")
    failed = 0
    for q in queries:
        year_from = CONCURRENT_FROM_YEAR if q["purpose"] == "concurrent" else None
        for src in sources:
            try:
                meta, records = SEARCHERS[src](q, year_from)
            except Exception as e:  # 单个请求失败不影响其他请求
                failed += 1
                row(q["id"], q["purpose"], src, "-", "-", "-", f"FAILED: {e}")
                continue
            meta = {"source_api": src, "query_id": q["id"], "purpose": q["purpose"],
                    "query_original": q["query"], "year_from": year_from, **meta,
                    "returned": len(records), "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            path = RAW_DIR / f"{src}_{q['id']}.json"
            path.write_text(json.dumps({"meta": meta, "records": records}, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
            no_id = sum(1 for r in records if not r["doi"] and not r["arxiv_id"])
            note = str(path.relative_to(ROOT))
            if year_from:
                note += f"  [year>={year_from}]"
            if len(meta.get("attempts", [])) > 1:
                note += "  [S2 fallback: core terms]"
            row(q["id"], q["purpose"], src, meta["total_hits"], len(records), no_id, note)

    total = len(queries) * len(sources)
    print(f"\n{total - failed}/{total} requests succeeded. "
          "total_hits = API-reported matches; saved = records kept (top {}); "
          "no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).".format(TOP_N))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
