"""Semantic Scholar：GET /graph/v1/paper/search/bulk。bulk 接口只匹配标题和摘要，支持布尔语法：AND 换成 +，OR 换成 |，
AND NOT (…) 换成 + -(…)；括号、引号短语和截断词（*）原样保留；未加引号的连字符词会被当成"排除"，改写成短语。
该接口不按相关度排序：按被引次数取回全部命中（最多 max_records 条，每页最多 1000 条，用 token 翻页，可从断点续跑），
再在本地重排（novelty_probe/sources/localrank.py）。
"""
import math
import urllib.parse

from .. import query as Q
from .. import schemas
from ..http import Token
from .base import Source
from .common import clean_arxiv, clean_doi
from .localrank import local_rank

URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = "title,year,externalIds,venue,journal,abstract,citationCount"
SORT = "citationCount:desc"
PAGE_SIZE = 1000


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


def citations(paper):
    return paper.get("citationCount") or 0


class SemanticScholar(Source):
    name = "semanticscholar"
    conversion = ("boolean -> S2 bulk syntax (AND -> +, OR -> |, AND NOT -> + -); phrases and prefix * kept; "
                  "re-ranked locally")
    paginates = True
    default_max_records = 3000
    capabilities = {"boolean": "api", "phrase": "api", "prefix": "api", "not": "api", "year_filter": "api",
                    "ranking": "local (groups matched, BM25, citations)"}
    url = URL

    def serialize(self, query, truncation):
        out, negate = [], False
        for tok, _ in query.tokens:
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

    def plan(self, top_n, max_records):
        return {"requests": max(1, math.ceil((max_records or self.default_max_records) / PAGE_SIZE)), "credits_per_request": 0}

    def search(self, item, year_from, ctx):
        parsed = Q.parse(item["query"])
        params = {"query": self.serialize(parsed, ctx.truncation), "fields": FIELDS, "sort": SORT}
        if year_from:
            params["year"] = f"{year_from}-"
        url = f"{self.url}?{urllib.parse.urlencode(params)}"
        max_records = ctx.max_records or self.default_max_records
        papers, total, pages, warnings, token = [], None, 0, [], None
        fetch = lambda base, p: ctx.fetch(f"{base}?{urllib.parse.urlencode(p)}")  # noqa: E731
        for page, items in ctx.client.paginate(self.url, params, scheme=Token(), max_items=max_records,
                                               checkpoint=ctx.checkpoint, fetch=fetch):
            if page.get("_resumed"):
                pages += page.get("pages", 0)
                papers.extend(items)
                continue
            pages += 1
            warnings.extend(schemas.s2_bulk(page))
            total = page.get("total") if total is None else total
            papers.extend(items)
            token = page.get("token")
        papers = papers[:max_records]
        ranked = local_rank(papers, parsed, ctx.top_n, citations)
        records = [{**s2_record(papers[i], item["id"]), "local_rank": info} for i, info in ranked]
        meta = {
            "conversion": self.conversion,
            "query_sent": params["query"],
            "request_url": url,
            "sort": "local: include groups matched, BM25 (title+abstract), citations; "
                    "records without abstract ranked separately and interleaved by their share",
            "retrieval_sort": SORT,
            "pool": {"retrieved": len(papers), "pages": pages, "truncated": bool(token) or len(papers) < (total or 0),
                     "with_abstract": sum(1 for p in papers if p.get("abstract")),
                     "same_title_dropped": sum(info.get("same_title_dropped", 0) for _, info in ranked)},
            "total_hits": total,
            "warnings": warnings,
        }
        return meta, records
