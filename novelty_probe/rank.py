"""候选排序（merge.py 的默认方法）：RRF 融合各结果列表的名次，BM25 打破并列；另记每篇满足几条检索式（n_conform）。

  rrf      Σ 1 / (rrf_k + 该篇在每个"检索式 × 来源"结果列表中的最好名次)，rrf_k 默认 60
  bm25     全部检索式的包含词在标题 + 摘要上的 BM25（k1、b 来自配置），排除组中的短语覆盖的位置不计
  n_conform 标题 + 摘要满足的检索式条数（按词干匹配；排除组按 NOT 判断）
排序：rrf 降序 → bm25 降序 → merged_id。
"""
from .record import list_ranks
from .text import BM25, Doc, query_match


def rrf(raw_refs, k):
    return round(sum(1 / (k + r) for r in list_ranks(raw_refs).values()), 6)


def score(merged, queries, rrf_k, k1, b):
    """给合并记录加上 rrf、bm25、n_conform。queries：{检索式 id: (包含组, 排除组)}。返回用到的词（写进 meta）。"""
    terms = list(dict.fromkeys(t for inc, _ in queries.values() for g in inc for t in g))
    ignore = list(dict.fromkeys(t for _, exc in queries.values() for g in exc for t in g))
    docs = [Doc(x["title"], x["abstract"]) for x in merged]
    bm = BM25(docs, terms, k1=k1, b=b)
    for i, (x, d) in enumerate(zip(merged, docs)):
        x["rrf"] = rrf(x["raw_refs"], rrf_k)
        x["bm25"] = round(bm.score(i, ignore), 3)
        x["n_conform"] = sum(query_match(inc, d, exc, ignore) for inc, exc in queries.values())
    return {"bm25_terms": terms, "ignored_phrases": ignore}


def sort_key(x):
    return (-x["rrf"], -x["bm25"], x["merged_id"])
