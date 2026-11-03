"""Crossref（默认关闭；配置 "sources": {"crossref": {"enabled": true}} 开启）：GET https://api.crossref.org/works?query.bibliographic=…

Crossref 的检索是词袋：不支持布尔运算、短语、截断与排除。适配方式是有损的，meta.lossy 逐条写明：
- 发送：包含组里的全部检索词合成一串（短语去掉引号，截断词换成配置 queries.truncation 中登记的完整词），按 Crossref 的相关度排序；
- 取回最多 max_records 条（默认 1000；每页最多 1000 条，cursor 翻页，可从断点续跑）；
- 本地判断：现有的文字须满足检索式（分组、短语、截断、排除）；没有摘要的只看标题，所以标题须满足整条检索式；
- 本地重排：与 Semantic Scholar 相同的排序键（满足的组数 → BM25 → 被引次数 is-referenced-by-count），取前 top_n 条。
total_hits 是 Crossref 对这串词的命中数，与布尔检索的命中数不可比；可比的是 pool.conforming（本地满足检索式的条数）。
Crossref 的题目与摘要常带 JATS / HTML 标记，去掉标签后保存；arXiv 的 DOI 由 DataCite 登记，不在 Crossref 里，所以 arxiv_id 总是空。
实测（2026-11-03，RUN_LOG Step 75–78）：教程的 v1 Q1、Q3、Q4 与 v2b Q2 各取前 40 条，本地满足检索式的都是 0 条——
query.bibliographic 面向参考文献匹配，常见词（generative AI、large language models）占满前列，区分性的词排不上来；
多数记录又没有摘要，只能看标题。两三个词的简单检索式效果好得多（tests/fixtures/crossref_queries.json）。
不收的条目类型：peer-review（审稿意见）、component（图表等组成部分）。
"""
import math
import urllib.parse
from dataclasses import dataclass

from .. import query as Q
from .. import schemas
from .base import Source
from .common import clean_doi, strip_markup
from .localrank import count_conforming, local_rank

URL = "https://api.crossref.org/works"
SELECT = "DOI,title,abstract,issued,container-title,type,is-referenced-by-count"
PAGE_SIZE = 1000
SKIP_TYPES = ("component", "peer-review")


@dataclass
class CrossrefCursor:
    """Crossref 的深翻页：参数 cursor=*，响应 message.next-cursor，条目在 message.items。"""
    param: str = "cursor"
    start: object = "*"
    stale_detail: str = ""

    def items_of(self, page):
        return (page.get("message") or {}).get("items") or []

    def next_of(self, page, state, n):
        nxt = (page.get("message") or {}).get("next-cursor")
        return nxt if (nxt and n) else None


def _first(values):
    return next((v for v in values or [] if v), None)


def crossref_record(item, qid):
    issued = ((item.get("issued") or {}).get("date-parts") or [[None]])[0] or [None]
    return {
        "title": strip_markup(_first(item.get("title"))),
        "year": issued[0],
        "doi": clean_doi(item.get("DOI")),
        "arxiv_id": None,
        "venue": _first(item.get("container-title")),
        "abstract": strip_markup(item.get("abstract")),
        "source_api": "crossref",
        "query_id": qid,
    }


class Crossref(Source):
    name = "crossref"
    conversion = "bag of words (include terms; truncated words -> full words); Boolean query applied locally; re-ranked locally"
    paginates = True
    default_max_records = 1000
    enabled_by_default = False
    capabilities = {"boolean": "local", "phrase": "local", "prefix": "expand + local", "not": "local", "year_filter": "api",
                    "ranking": "local (groups matched, BM25, citations)"}
    url = URL
    lossy = [
        "Crossref has no Boolean operators, phrase search, truncation or exclusion: all include terms are sent as one bag of words",
        "truncated words are replaced by their registered full words",
        "the Boolean query (groups, phrases, truncation, NOT) is applied locally to title + abstract; a record without "
        "an abstract is kept only if its title alone satisfies the query",
        "record types not kept: " + ", ".join(SKIP_TYPES),
        "total_hits is Crossref's count for the bag of words, not comparable with Boolean hit counts; see pool.conforming",
    ]

    def serialize(self, query, truncation):
        words = []
        for term in query.terms():
            if term.kind == "prefix":
                if term.raw not in truncation:
                    raise Q.QueryError("Q201", "query.unregistered_truncation", term.pos, tok=term.raw)
                words.append(truncation[term.raw])
            else:
                words.append(term.text)
        return " ".join(dict.fromkeys(words))

    def plan(self, top_n, max_records):
        return {"requests": max(1, math.ceil((max_records or self.default_max_records) / PAGE_SIZE)), "credits_per_request": 0}

    def search(self, item, year_from, ctx):
        parsed = Q.parse(item["query"])
        max_records = ctx.max_records or self.default_max_records
        params = {"query.bibliographic": self.serialize(parsed, ctx.truncation), "rows": min(PAGE_SIZE, max_records),
                  "select": SELECT, "sort": "relevance", "order": "desc"}
        if year_from:
            params["filter"] = f"from-pub-date:{year_from}-01-01"
        url = f"{self.url}?{urllib.parse.urlencode(params)}"
        items, total, pages, warnings, more = [], None, 0, [], False
        fetch = lambda base, p: ctx.fetch(f"{base}?{urllib.parse.urlencode(p)}")  # noqa: E731
        for page, got in ctx.client.paginate(self.url, params, scheme=CrossrefCursor(), max_items=max_records,
                                             checkpoint=ctx.checkpoint, fetch=fetch):
            if page.get("_resumed"):
                pages += page.get("pages", 0)
                items.extend(got)
                continue
            pages += 1
            warnings.extend(schemas.crossref_list(page))
            msg = page.get("message") or {}
            total = msg.get("total-results") if total is None else total
            items.extend(got)
            more = bool(got) and bool(msg.get("next-cursor"))
        items = items[:max_records]
        kept = [it for it in items if it.get("type") not in SKIP_TYPES]
        recs = [crossref_record(it, item["id"]) for it in kept]
        papers = [{**r, "_cites": it.get("is-referenced-by-count") or 0} for r, it in zip(recs, kept)]
        ranked = local_rank(papers, parsed, ctx.top_n, citations=lambda p: p["_cites"], require_conform=True)
        records = [{**recs[i], "local_rank": info} for i, info in ranked]
        meta = {
            "conversion": self.conversion,
            "query_sent": params["query.bibliographic"],
            "request_url": url,
            "lossy": self.lossy,
            "sort": "local: include groups matched, BM25 (title+abstract), citations; "
                    "records without abstract ranked separately and interleaved by their share",
            "retrieval_sort": "relevance",
            "pool": {"retrieved": len(items), "pages": pages, "truncated": more or len(items) < (total or 0),
                     "with_abstract": sum(1 for r in recs if r.get("abstract")),
                     "skipped_types": len(items) - len(kept),
                     "conforming": count_conforming(recs, parsed),
                     "same_title_dropped": sum(info.get("same_title_dropped", 0) for _, info in ranked)},
            "total_hits": total,
            "warnings": warnings,
        }
        return meta, records
