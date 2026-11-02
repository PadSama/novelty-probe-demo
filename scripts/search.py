#!/usr/bin/env python3
"""novelty-probe 检索脚本。

对 queries/queries.json 中的每条检索式，分别查询
  - OpenAlex          GET https://api.openalex.org/works?filter=title_and_abstract.search:...
  - Semantic Scholar  GET https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=...
各取前 25 条（OpenAlex 按相关度，S2 按被引次数），原样存到 results/raw/{source}_{query_id}{suffix}.json
（suffix 默认为空；v2 用 --queries queries/queries_v2.json --suffix _v2），并在终端打印命中数。

输出文件结构：{"meta": {...}, "records": [...]}
  meta    实际发送的检索串、请求地址、排序方式、API 报告的总命中数、检索时间等。
  records 每条只有 title, year, doi, arxiv_id, venue, abstract, source_api, query_id，
          按 API 返回顺序保存，不去重、不筛选。值直接取自 API 返回，只做格式整理：
          DOI 去掉 https://doi.org/ 前缀；arXiv ID 去掉版本号；OpenAlex 摘要由倒排索引还原；
          OpenAlex 没有 arXiv 字段，arxiv_id 取自 arXiv DOI（10.48550/arXiv.*）或 arxiv.org 链接。

检索式转换（queries.json 是通用布尔写法；以下行为均于 2026-10-31 实测）：
  OpenAlex          用 filter=title_and_abstract.search 只匹配标题和摘要（与 S2 bulk 一致），按 relevance_score
                    降序取前 25 条。默认的 search= 会匹配全文，实测其前 25 条多数在标题和摘要里不满足检索式。
                    支持 AND / OR、括号和引号短语，照原样发送；不支持通配符（返回 400，要求改用不做词干还原的
                    search.exact），所以截断词（*）换成完整词，词形变化交给默认的词干还原。
                    filter 用逗号分隔条件，所以检索式里不能有逗号。
                    meta 中记录 OpenAlex 对检索式的解析结果（x_query.oql），便于核对。
  Semantic Scholar  bulk 接口只匹配标题和摘要，支持布尔语法：AND 换成 +，OR 换成 |，
                    括号、引号短语和截断词（*）原样保留。该接口不按相关度排序，
                    "前 25 条"按被引次数从高到低取（sort=citationCount:desc）。
  purpose 为 concurrent 的检索式只取 2023 年起的文献（facets/facets.md 中的约定）。

可选环境变量（不会写进输出文件）：
  OPENALEX_API_KEY  本云环境中 key 已由 Network secrets 在代理层注入，无需设置；在本机运行时才需要。
  S2_API_KEY        不设也能运行，但匿名请求共用限流池，容易返回 429。本云环境中研究者已为 api.semanticscholar.org
                    配置了 key（2026-11-02）。有 key 时的限额是每秒 1 个请求、所有接口合计，所以脚本对发往
                    api.semanticscholar.org 的每个请求（含翻页与重试）统一节流，间隔不少于 S2_MIN_INTERVAL 秒。
                    不要同时运行两个会访问 S2 的脚本。

用法：
  python3 scripts/search.py                                  # 全部检索式 × 两个来源
  python3 scripts/search.py --ids Q1,Q3 --sources semanticscholar
  python3 scripts/search.py --queries queries/queries_v2.json --suffix _v2
  python3 scripts/search.py --dry-run                        # 不联网，只检查检索式语法
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

from textmatch import BM25, Doc, groups_matched, title_key

ROOT = Path(__file__).resolve().parent.parent
QUERIES_FILE = ROOT / "queries" / "queries.json"
RAW_DIR = ROOT / "results" / "raw"

TOP_N = 25
CONCURRENT_FROM_YEAR = 2023
USER_AGENT = "novelty-probe/0.1 (literature search script)"
OPENALEX_URL = "https://api.openalex.org/works"
OPENALEX_SORT = "relevance_score:desc"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_FIELDS = "title,year,externalIds,venue,journal,abstract,citationCount"
S2_SORT = "citationCount:desc"
S2_MAX_RECORDS = 3000  # 本地重排时最多取多少条（bulk 每页最多 1000 条，用 token 翻页）
S2_HOST = "api.semanticscholar.org"
S2_MIN_INTERVAL = 1.1  # S2 的限额：每秒 1 个请求，所有接口合计；留一点余量
MAX_RETRY_WAIT = 60  # 服务端要求等待超过这么多秒（如 OpenAlex 每日额度用完）就不重试，直接报错

# 截断词 → 完整词（只用于 OpenAlex）。遇到未登记的截断词就报错，避免悄悄改变检索含义。
TRUNCATION = {
    "bibliometric*": "bibliometrics",
    "economist*": "economists",
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


def parse_query(query):
    """'A AND (B OR C) AND NOT (D OR E)' → ([['A'], ['B', 'C']], [['D', 'E']])，即（包含组，排除组）。
    写法：顶层用 AND 连接若干组；组是单个词或括号内用 OR 连接的词；排除组写成 AND NOT 组，放在包含组之后。
    不支持嵌套括号、括号内的 AND、括号外的 OR；其他写法直接报错。"""
    include, exclude, cur, depth, negate = [], [], [], 0, False
    for tok in TOKEN_RE.findall(query):
        if tok == "(":
            depth += 1
            if depth > 1:
                raise ValueError("不支持嵌套括号")
        elif tok == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("括号不配对")
        elif tok == "AND":
            if depth:
                raise ValueError("不支持括号内的 AND")
            (exclude if negate else include).append(cur)
            cur, negate = [], False
        elif tok == "OR":
            if not depth:
                raise ValueError("不支持括号外的 OR")
        elif tok == "NOT":
            if not include and not cur:
                raise ValueError("检索式不能以 NOT 开头")
            if depth or cur or negate:
                raise ValueError('NOT 只能写在 AND 之后、作为一个组的开头，例如 … AND NOT ("a" OR "b")')
            negate = True
        elif tok.upper() in ("AND", "OR", "NOT"):
            # OpenAlex 把小写的 not 当作普通词、整句改按 AND 处理（实测会把排除变成包含），一律要求大写
            raise ValueError(f"运算符必须大写：{tok} → {tok.upper()}；如果它是检索词，请加引号")
        elif tok[0] in "-!":
            raise ValueError(f"不支持用 {tok[0]} 表示排除（{tok}），请写成 AND NOT (…)")
        else:
            cur.append(tok)
    (exclude if negate else include).append(cur)
    if depth or not all(include) or not all(exclude):
        raise ValueError("括号不配对或存在空的组")
    if not include:
        raise ValueError("至少需要一个不带 NOT 的组")
    return include, exclude


def and_groups(query):
    """检索式的包含组（排除组见 parse_query）。"""
    return parse_query(query)[0]


def to_openalex(query):
    """通用布尔式 → OpenAlex：照原样发送（AND / OR / NOT 均为 OpenAlex 原生语法，必须大写），截断词换成完整词。"""
    parse_query(query)  # 只做语法检查
    if "," in query:
        raise ValueError("OpenAlex 的 filter 用逗号分隔条件，检索式里不能有逗号")
    return expand_truncation(query)


def to_s2_bulk(query):
    """通用布尔式 → S2 bulk 语法：AND → +，OR → |，AND NOT (…) → + -(…)；括号、引号短语、截断词原样保留。"""
    parse_query(query)  # 只做语法检查
    out, negate = [], False
    for tok in TOKEN_RE.findall(query):
        if tok == "AND":
            out.append("+")
            continue
        if tok == "OR":
            out.append("|")
            continue
        if tok == "NOT":
            negate = True
            continue
        if "-" in tok and not tok.startswith('"'):
            # 未加引号的连字符词在 S2 语法里会被当成"排除"，改写成短语
            tok = '"' + tok.replace("-", " ") + '"'
        out.append("-" + tok if negate else tok)
        negate = False
    return " ".join(out).replace("( ", "(").replace(" )", ")")


# ---------- HTTP ----------

def api_error(e):
    """从 HTTP 错误响应里取出简短说明（优先取 JSON 的 message / error 字段）。"""
    raw = e.read(2000).decode("utf-8", "replace")
    try:
        body = json.loads(raw)
        msg = body.get("message") or body.get("error") or raw
    except (ValueError, AttributeError):
        msg = raw
    msg = " ".join(str(msg).split())
    return msg[:200] + ("…" if len(msg) > 200 else "")


_last_s2_request = [float("-inf")]


def throttle(url):
    """发往 Semantic Scholar 的请求之间至少间隔 S2_MIN_INTERVAL 秒（每个请求、每次重试都算一次）。"""
    if urllib.parse.urlsplit(url).hostname != S2_HOST:
        return
    wait = _last_s2_request[0] + S2_MIN_INTERVAL - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_s2_request[0] = time.monotonic()


def get_json(url, headers=None, retries=5):
    """GET 并解析 JSON。429、5xx、超时、连接被重置时指数退避重试；
    服务端要求等待超过 MAX_RETRY_WAIT 秒时不重试。其他错误直接抛出
    （包括代理拒绝连接：那是网络策略问题，重试没有用）。发往 S2 的请求先经 throttle() 节流。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(retries + 1):
        wait = 2 ** (attempt + 1)
        throttle(url)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            retry_after = e.headers.get("Retry-After", "")
            retry_after = int(retry_after) if retry_after.isdigit() else 0
            if (e.code == 429 or e.code >= 500) and attempt < retries and retry_after <= MAX_RETRY_WAIT:
                time.sleep(max(wait, retry_after))
                continue
            raise RuntimeError(f"HTTP {e.code}: {api_error(e)}") from None
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
    query_sent = to_openalex(q["query"])
    filters = [f"title_and_abstract.search:{query_sent}"]
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    params = {"filter": ",".join(filters), "sort": OPENALEX_SORT, "per-page": TOP_N, "page": 1}
    key = os.environ.get("OPENALEX_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}  # key 放请求头，不进 URL
    url = f"{OPENALEX_URL}?{urllib.parse.urlencode(params)}"
    data = get_json(url, headers)
    time.sleep(0.2)
    api_meta = data.get("meta") or {}
    oql = (api_meta.get("x_query") or {}).get("oql")
    if parse_query(q["query"])[1] and oql and " NOT " not in oql:
        # 例如 not 写成了小写：OpenAlex 会静默改按 AND 处理，把要排除的内容变成必须包含
        raise RuntimeError(f"OpenAlex 没有把排除组解析为 NOT（oql: {oql[:160]}），结果未保存")
    records = [openalex_record(w, q["id"]) for w in (data.get("results") or [])[:TOP_N]]
    meta = {
        "conversion": "boolean kept; truncated words -> full words; matched on title and abstract",
        "query_sent": query_sent,
        "api_interpretation": (api_meta.get("x_query") or {}).get("oql"),
        "request_url": url,
        "sort": OPENALEX_SORT,
        "total_hits": api_meta.get("count"),
    }
    return meta, records


def s2_local_rank(papers, query, top_n=TOP_N):
    """S2 bulk 不按相关度排序：在取回的记录上本地重排，返回 [(下标, 打分说明)]，最多 top_n 条。
    排序键：满足的包含组数（按词干匹配标题 + 摘要）→ BM25（k1=1.2，b=0.75，短语按整体计）→ 被引次数。
    没有摘要的记录（S2 常因出版商限制不给摘要）只能按标题打分，单独排序：标题至少命中（组数 − 1）个包含组的，
    按无摘要记录在全部记录中的比例分配名额、按名次穿插，免得只因缺摘要就沉底；其余排在最后。
    标题完全相同的记录只保留排在最前的一条（其 same_title_dropped 记去掉了几条）。"""
    include, exclude = parse_query(query)
    ignore = [t for g in exclude for t in g]
    docs = [Doc(p.get("title"), p.get("abstract")) for p in papers]
    bm = BM25(docs, [t for g in include for t in g])
    info = {i: {"groups_matched": groups_matched(include, d, ignore), "bm25": round(bm.score(i, ignore), 3),
                "has_abstract": bool(papers[i].get("abstract")), "citations": papers[i].get("citationCount") or 0}
            for i, d in enumerate(docs)}
    key = lambda i: (-info[i]["groups_matched"], -info[i]["bm25"], -info[i]["citations"], i)  # noqa: E731
    # 标题完全相同的记录（如在多期重复刊登、各有 DOI 的征稿启事）只保留排在最前的一条，免得占满名额
    first_of_title = {}
    for i in sorted(info, key=lambda i: (not info[i]["has_abstract"],) + key(i)):
        tk = title_key(papers[i].get("title"))
        if tk and tk in first_of_title:
            info[first_of_title[tk]]["same_title_dropped"] = info[first_of_title[tk]].get("same_title_dropped", 0) + 1
            info[i]["dropped"] = True
        elif tk:
            first_of_title[tk] = i
    with_abs = sorted((i for i in info if info[i]["has_abstract"] and not info[i].get("dropped")), key=key)
    without = sorted((i for i in info if not info[i]["has_abstract"] and not info[i].get("dropped")), key=key)
    threshold = max(1, len(include) - 1)
    eligible = [i for i in without if info[i]["groups_matched"] >= threshold]
    rest = [i for i in without if info[i]["groups_matched"] < threshold]
    n = min(top_n, len(with_abs) + len(without))
    pool = len(with_abs) + len(without)
    n_without = min(round(n * len(without) / pool) if pool else 0, len(eligible))
    n_with = min(n - n_without, len(with_abs))
    n_without = min(n - n_with, len(eligible))
    picked = [((k + 0.5) / n_with, 0, i) for k, i in enumerate(with_abs[:n_with])]
    picked += [((k + 0.5) / n_without, 1, i) for k, i in enumerate(eligible[:n_without])]
    order = [i for _, _, i in sorted(picked)] + rest[:n - n_with - n_without]
    return [(i, info[i]) for i in order]


def search_s2(q, year_from):
    key = os.environ.get("S2_API_KEY")
    headers = {"x-api-key": key} if key else {}
    params = {"query": to_s2_bulk(q["query"]), "fields": S2_FIELDS, "sort": S2_SORT}
    if year_from:
        params["year"] = f"{year_from}-"
    url = f"{S2_URL}?{urllib.parse.urlencode(params)}"
    papers, total, token, pages = [], None, None, 0
    while True:  # 翻页取回记录（最多 S2_MAX_RECORDS 条），再在本地按相关度重排
        page_url = url + (f"&{urllib.parse.urlencode({'token': token})}" if token else "")
        data = get_json(page_url, headers)  # 节流在 get_json 中统一处理
        pages += 1
        total = data.get("total") if total is None else total
        papers.extend(data.get("data") or [])
        token = data.get("token")
        if not token or len(papers) >= S2_MAX_RECORDS:
            break
    papers = papers[:S2_MAX_RECORDS]
    ranked = s2_local_rank(papers, q["query"])
    records = [{**s2_record(papers[i], q["id"]), "local_rank": info} for i, info in ranked]
    meta = {
        "conversion": "boolean -> S2 bulk syntax (AND -> +, OR -> |, AND NOT -> + -); phrases and prefix * kept; "
                      "re-ranked locally",
        "query_sent": params["query"],
        "request_url": url,
        "sort": "local: include groups matched, BM25 (title+abstract), citations; "
                "records without abstract ranked separately and interleaved by their share",
        "retrieval_sort": S2_SORT,
        "pool": {"retrieved": len(papers), "pages": pages, "truncated": bool(token) or len(papers) < (total or 0),
                 "with_abstract": sum(1 for p in papers if p.get("abstract")),
                 "same_title_dropped": sum(info.get("same_title_dropped", 0) for _, info in ranked)},
        "total_hits": total,
    }
    return meta, records


SEARCHERS = {"openalex": search_openalex, "semanticscholar": search_s2}
PURPOSES = {"component", "application", "method", "concurrent"}
ID_RE = re.compile(r"^Q\d+$")  # merge.py 只读取 {source}_Q<数字>{suffix}.json，id 必须是这种格式


def load_queries(path):
    """读取并校验检索式文件；有问题时抛出 ValueError，列出所有问题。"""
    try:
        queries = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} 不是合法的 JSON（第 {e.lineno} 行）：{e.msg}") from None
    if not isinstance(queries, list) or not queries:
        raise ValueError(f"{path} 应为非空的 JSON 数组")
    problems, seen = [], set()
    for i, q in enumerate(queries, 1):
        if not isinstance(q, dict):
            problems.append(f"第 {i} 条不是对象")
            continue
        qid = q.get("id")
        if not isinstance(qid, str) or not ID_RE.match(qid):
            problems.append(f"第 {i} 条的 id {qid!r} 应为 Q1、Q2 这样的格式")
        elif qid in seen:
            problems.append(f"id {qid} 重复")
        seen.add(qid)
        if not isinstance(q.get("query"), str) or not q["query"].strip():
            problems.append(f"{qid or f'第 {i} 条'} 缺少 query")
        if q.get("purpose") not in PURPOSES:
            problems.append(f"{qid or f'第 {i} 条'} 的 purpose {q.get('purpose')!r} 应为 {'/'.join(sorted(PURPOSES))} 之一")
    if problems:
        raise ValueError("检索式文件有问题：\n  " + "\n  ".join(problems))
    return queries


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser(description="Run queries/queries.json against OpenAlex and Semantic Scholar.")
    ap.add_argument("--ids", help="只跑这些检索式，逗号分隔，如 Q1,Q3")
    ap.add_argument("--sources", default=",".join(SEARCHERS), help="逗号分隔：openalex,semanticscholar")
    ap.add_argument("--queries", type=Path, default=QUERIES_FILE, help="检索式文件，默认 queries/queries.json")
    ap.add_argument("--suffix", default="", help="输出文件名后缀，如 _v2")
    ap.add_argument("--dry-run", action="store_true", help="不联网：只检查检索式语法并打印各来源实际会发送的检索串")
    args = ap.parse_args()

    try:
        queries = load_queries(args.queries)
    except (OSError, ValueError) as e:
        print(e)
        return 2
    qfile = args.queries.resolve()
    qfile = str(qfile.relative_to(ROOT)) if qfile.is_relative_to(ROOT) else str(qfile)
    if args.ids:
        wanted = set(args.ids.split(","))
        missing = wanted - {q["id"] for q in queries}
        if missing:
            ap.error(f"检索式文件中没有这些 id：{', '.join(sorted(missing))}")
        queries = [q for q in queries if q["id"] in wanted]
    sources = args.sources.split(",")
    unknown = set(sources) - set(SEARCHERS)
    if unknown:
        ap.error(f"未知来源：{', '.join(sorted(unknown))}")
    if args.dry_run:
        bad = 0
        for q in queries:
            try:
                print(f"{q['id']} [{q['purpose']}]\n  openalex:        {to_openalex(q['query'])}"
                      f"\n  semanticscholar: {to_s2_bulk(q['query'])}")
            except ValueError as e:
                bad += 1
                print(f"{q['id']} INVALID: {e}\n  query: {q['query']}")
        print(f"\n{len(queries) - bad}/{len(queries)} queries valid (dry run, nothing sent)")
        return 1 if bad else 0
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
                    "queries_file": qfile,
                    "query_original": q["query"], "year_from": year_from, **meta,
                    "returned": len(records), "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            path = RAW_DIR / f"{src}_{q['id']}{args.suffix}.json"
            path.write_text(json.dumps({"meta": meta, "records": records}, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
            no_id = sum(1 for r in records if not r["doi"] and not r["arxiv_id"])
            note = str(path.relative_to(ROOT)) if path.resolve().is_relative_to(ROOT) else str(path)
            if year_from:
                note += f"  [year>={year_from}]"
            row(q["id"], q["purpose"], src, meta["total_hits"], len(records), no_id, note)

    total = len(queries) * len(sources)
    print(f"\n{total - failed}/{total} requests succeeded. total_hits = API-reported matches; "
          f"saved = records kept (top {TOP_N}: OpenAlex by API relevance, S2 re-ranked locally by relevance); "
          "no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
