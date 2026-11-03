"""不按相关度排序的数据源（S2 bulk、Crossref）在取回的记录上本地重排。"""
from .. import query as Q
from ..text import BM25, Doc, groups_matched, query_match, term_in, title_key  # noqa: F401


def excluded(doc, exclude):
    """文中是否出现任何排除词。"""
    return any(term_in(w, doc) for g in exclude for w in g)


def conforms(doc, include, exclude, ignore):
    """数据源本身不做布尔检索时（Crossref）的本地判断：现有的文字（标题 + 摘要；没有摘要时只有标题）须满足检索式。
    与 S2 不同：S2 的服务器已按标题与摘要做过布尔检索，无摘要记录只是本地看不到摘要；Crossref 没有，标题不满足就无从证明。"""
    return query_match(include, doc, exclude, ignore)


def count_conforming(papers, query):
    """按 conforms() 的标准，满足检索式的记录数。"""
    q = Q.parse(query) if isinstance(query, str) else query
    include, exclude = q.lists()
    ignore = [w for g in exclude for w in g]
    return sum(conforms(Doc(p.get("title"), p.get("abstract")), include, exclude, ignore) for p in papers)


def local_rank(papers, query, top_n, citations, require_conform=False):
    """返回 [(下标, 打分说明)]，最多 top_n 条。
    排序键：满足的包含组数（按词干匹配标题 + 摘要）→ BM25（k1=1.2，b=0.75，短语按整体计）→ 被引次数。
    没有摘要的记录只能按标题打分，单独排序：标题至少命中（组数 − 1）个包含组的，按无摘要记录在全部记录中的比例分配名额、
    按名次穿插，免得只因缺摘要就沉底；其余排在最后。标题完全相同的记录只保留排在最前的一条（same_title_dropped 记去掉几条）。
    require_conform：数据源本身不做布尔检索时（Crossref）为 True，先丢掉现有文字不满足检索式的记录（见 conforms）。"""
    q = Q.parse(query) if isinstance(query, str) else query
    include, exclude = q.lists()
    ignore = [w for g in exclude for w in g]
    docs = [Doc(p.get("title"), p.get("abstract")) for p in papers]
    bm = BM25(docs, [w for g in include for w in g])
    info = {i: {"groups_matched": groups_matched(include, d, ignore), "bm25": round(bm.score(i, ignore), 3),
                "has_abstract": bool(papers[i].get("abstract")), "citations": citations(papers[i])}
            for i, d in enumerate(docs)}
    threshold = max(1, len(include) - 1)
    if require_conform:
        for i, d in enumerate(docs):
            if not conforms(d, include, exclude, ignore):
                info[i]["dropped"] = info[i]["nonconforming"] = True
    key = lambda i: (-info[i]["groups_matched"], -info[i]["bm25"], -info[i]["citations"], i)  # noqa: E731
    # 标题完全相同的记录（如在多期重复刊登、各有 DOI 的征稿启事）只保留排在最前的一条，免得占满名额
    first_of_title = {}
    for i in sorted((i for i in info if not info[i].get("nonconforming")), key=lambda i: (not info[i]["has_abstract"],) + key(i)):
        tk = title_key(papers[i].get("title"))
        if tk and tk in first_of_title:
            info[first_of_title[tk]]["same_title_dropped"] = info[first_of_title[tk]].get("same_title_dropped", 0) + 1
            info[i]["dropped"] = True
        elif tk:
            first_of_title[tk] = i
    with_abs = sorted((i for i in info if info[i]["has_abstract"] and not info[i].get("dropped")), key=key)
    without = sorted((i for i in info if not info[i]["has_abstract"] and not info[i].get("dropped")), key=key)
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
    return [(i, {k: v for k, v in info[i].items() if k not in ("dropped", "nonconforming")}) for i in order]
