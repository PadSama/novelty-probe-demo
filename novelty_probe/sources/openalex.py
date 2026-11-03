"""OpenAlex：GET /works?filter=title_and_abstract.search:<检索式>，按 relevance_score 降序取前 top_n 条。

检索式照原文发送（AND / OR / NOT、括号、引号短语都是 OpenAlex 原生语法，必须大写）；OpenAlex 的默认检索不支持通配符
（返回 400），截断词换成配置 queries.truncation 中登记的完整词，未登记的报 Q201。filter 用逗号分隔条件，检索式里不能有逗号
（解析时已检查，Q111）。OpenAlex 对格式错误的检索式不报错而静默改写，所以保存结果前核对它返回的解析结果（meta.x_query）：
运算符被当成引号内的词、有排除组却没有 NOT、分组结构与发送的不同，都报错不保存；解析树结构不认识时只记警告。
"""
import re
import urllib.parse
from collections import Counter

from .. import query as Q
from .. import schemas
from ..i18n import t
from .base import Source
from .common import ARXIV_DOI_RE, ARXIV_URL_RE, author_fields, clean_arxiv, clean_doi, rebuild_abstract

URL = "https://api.openalex.org/works"
SORT = "relevance_score:desc"
CREDITS_PER_LIST_REQUEST = 10      # 实测：带检索条件的列表请求每次 10 credits；按 DOI 取单篇、400 / 404 不计
_TRUNC_RE = re.compile(r"[A-Za-z][\w-]*\*")
_QUOTED_OPERATOR_RE = re.compile(r'"(?:AND|OR|NOT|and|or|not)"')
_SEARCH_COLUMN = "title_and_abstract.search"


def expand_truncation(text, truncation):
    """检索式原文中的截断词换成登记的完整词；未登记的报 Q201（标出位置）。"""
    def repl(m):
        tok = m.group(0)
        if tok not in truncation:
            raise Q.QueryError("Q201", "query.unregistered_truncation", m.start(), tok=tok)
        return truncation[tok]
    return _TRUNC_RE.sub(repl, text)


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


def openalex_authors(work):
    """作者名（authorships 按署名顺序）；响应里没有 authorships 时返回 None。"""
    if "authorships" not in work:
        return None
    return [((a or {}).get("author") or {}).get("display_name") or (a or {}).get("raw_author_name")
            for a in work.get("authorships") or []]


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
        **author_fields(openalex_authors(work)),
        "source_api": "openalex",
        "query_id": qid,
    }


# ---------- 核对 OpenAlex 的解析结果 ----------

def _norm(value):
    return " ".join(str(value or "").strip().strip('"').lower().split())


def tree_groups(oqo):
    """OpenAlex 的解析树（x_query.oqo）→ (包含组 [frozenset], 排除词 set)；结构不认识时返回 None。
    已知结构（2026-11 实测）：filter_rows 各行相互 AND；一行是单个词，或 {"join": "or", "filters": [词, …]}；
    排除组 NOT (a OR b) 展开为两个 "is_negated": true 的词。title_and_abstract.search 以外的行（如发表日期）不参与比对。"""
    rows = (oqo or {}).get("filter_rows")
    if not isinstance(rows, list):
        return None
    include, exclude = [], set()
    for row in rows:
        if not isinstance(row, dict):
            return None
        if "join" in row:
            leaves = row.get("filters")
            if row.get("join") != "or" or not isinstance(leaves, list) or not leaves:
                return None
            values = set()
            for leaf in leaves:
                if (not isinstance(leaf, dict) or "join" in leaf or leaf.get("column_id") != _SEARCH_COLUMN
                        or leaf.get("is_negated") or leaf.get("operator") not in (None, "has")):
                    return None
                values.add(_norm(leaf.get("value")))
            if row.get("is_negated"):
                exclude |= values          # NOT (a OR b) 与 NOT a AND NOT b 等价
            else:
                include.append(frozenset(values))
        elif row.get("column_id") == _SEARCH_COLUMN:
            if row.get("operator") not in (None, "has"):
                return None
            if row.get("is_negated"):
                exclude.add(_norm(row.get("value")))
            else:
                include.append(frozenset([_norm(row.get("value"))]))
    return include, exclude


def _describe(include, exclude):
    groups = sorted("(" + " OR ".join(sorted(g)) + ")" if len(g) > 1 else next(iter(g)) for g in include)
    text = " AND ".join(groups)
    return text + (" NOT (" + " OR ".join(sorted(exclude)) + ")" if exclude else "")


def check_interpretation(query_sent, api_meta):
    """核对 OpenAlex 对检索式的解析（meta.x_query）。返回警告列表；与意图不同时抛 RuntimeError（结果不保存）：
    - 运算符被当成了引号内的词（如未配对的引号：("a OR b) AND c → (a "OR" b "AND" c)）；
    - 有排除组却没有解析出 NOT（如小写 not）；
    - 解析树（oqo）的分组与发送的检索式不同（逐组比较词集合，组的顺序与组内词序不计）。
    解析树结构不认识时记一条警告，退回只比较词集合。"""
    xq = api_meta.get("x_query") or {}
    oql = xq.get("oql") or ""
    if _QUOTED_OPERATOR_RE.search(oql):
        raise RuntimeError(t("openalex.quoted_operators", oql=oql[:160]))
    parsed = Q.parse(query_sent)
    if parsed.exclude and oql and " NOT " not in oql:
        raise RuntimeError(t("openalex.no_not", oql=oql[:160]))
    oqo = xq.get("oqo")
    if not oqo:
        return []
    want_inc = Counter(frozenset(_norm(term.text) for term in g.terms) for g in parsed.include)
    want_exc = {_norm(term.text) for term in parsed.terms(negated=True)}
    got = tree_groups(oqo)
    if got is not None:
        got_inc, got_exc = Counter(got[0]), got[1]
        if got_inc != want_inc or got_exc != want_exc:
            raise RuntimeError(t("openalex.group_mismatch", sent=_describe(want_inc.elements(), want_exc),
                                 got=_describe(got_inc.elements(), got_exc)))
        return []
    # 结构不认识：只比较词集合
    leaves = set()

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("value"), str):
                leaves.add(_norm(node["value"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(oqo.get("filter_rows"))
    ours = {term for g in want_inc for term in g} | want_exc
    warnings = [t("openalex.unknown_tree")]
    if leaves and leaves != ours:
        warnings.append(t("openalex.term_mismatch", extra=sorted(leaves - ours), missing=sorted(ours - leaves)))
    return warnings


class OpenAlex(Source):
    name = "openalex"
    conversion = "boolean kept; truncated words -> full words; matched on title and abstract"
    capabilities = {"boolean": "api", "phrase": "api", "prefix": "expand", "not": "api", "year_filter": "api",
                    "ranking": "api (relevance_score)"}
    label = "OpenAlex"
    interface = "GET https://api.openalex.org/works?filter=title_and_abstract.search:…"
    ranking = ("API 相关度（relevance_score）", "API relevance (relevance_score)")
    url = URL

    def serialize(self, query, truncation):
        return expand_truncation(query.raw, truncation)

    def plan(self, top_n, max_records):
        return {"requests": 1, "credits_per_request": CREDITS_PER_LIST_REQUEST}

    def search(self, item, year_from, ctx):
        query_sent = self.serialize(Q.parse(item["query"]), ctx.truncation)
        filters = [f"title_and_abstract.search:{query_sent}"]
        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")
        params = {"filter": ",".join(filters), "sort": SORT, "per-page": ctx.top_n, "page": 1}
        url = f"{self.url}?{urllib.parse.urlencode(params)}"
        data = ctx.fetch(url)  # key 由客户端放进请求头，不进 URL
        api_meta = data.get("meta") or {}
        warnings = schemas.openalex_list(data) + check_interpretation(query_sent, api_meta)
        records = [openalex_record(w, item["id"]) for w in (data.get("results") or [])[:ctx.top_n]]
        meta = {
            "conversion": self.conversion,
            "query_sent": query_sent,
            "api_interpretation": (api_meta.get("x_query") or {}).get("oql"),
            "api_parse_tree": (api_meta.get("x_query") or {}).get("oqo"),
            "request_url": url,
            "sort": SORT,
            "total_hits": api_meta.get("count"),
            "warnings": warnings,
        }
        return meta, records
