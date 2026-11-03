"""合并记录：同一篇文献的多条原始记录（不同来源、检索式与版本）组装成一条（merge.py 的默认方法）。

字段取值（值都取自原始记录，只做格式整理；field_source 记每个字段取自哪条原始记录，形如 openalex_Q1#3）：
  title      第一个非空标题（按来源顺序 → 检索式编号 → 名次）
  doi        正式发表版本的 DOI 优先（不是预印本前缀的），其余 DOI 与 arXiv ID 进 alt_ids
  year       正式发表版本的年份（同一 DOI 中不带 arXiv ID 的记录 → OpenAlex 的记录 → 最早）；year_first 为全部记录中最早的年份
  venue      第一个不是 arXiv 的出处
  abstract   最长的一份摘要
  authors    第一条带作者的记录的作者（最多 20 位）；n_authors 为该记录的作者总数
旧的原始结果文件没有作者，authors、n_authors 为 None，其余字段与阶段 3 相同。
"""
import re

from .text import norm_doi

SCHEMA = "novelty-probe/merged@2"
ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.I)
# 预印本平台的版本 DOI，如 10.31234/osf.io/abcde_v2、10.36227/techrxiv.123.456/v1、10.21203/rs.3.rs-123/v1
PREPRINT_VERSION_RE = re.compile(r"^(10\.\d+/(?:osf\.io/\w+?|techrxiv\.[\d.]+|rs\.\d+\.rs-\d+))[_/]v\d+$", re.I)


def first(values):
    return next((v for v in values if v), None)


def qnum(qid):
    return int(re.sub(r"\D", "", qid) or 0)


def list_ranks(raw_refs):
    """{结果列表: 该篇在列表中的最好名次}；raw_refs 形如 openalex_Q1#8。"""
    best = {}
    for ref in raw_refs:
        lst, rank = ref.rsplit("#", 1)
        best[lst] = min(best.get(lst, int(rank)), int(rank))
    return best


def clean_doi(doi):
    """显示用的 DOI：去掉误入 DOI 字段的 URL 查询串与落地页后缀（如 /full/html?utm_source=…），保留大小写。"""
    if not doi:
        return doi
    d = re.split(r"[?#]", doi.strip())[0]
    return re.sub(r"/(?:full|abstract|pdf|epdf|html)(?:/html)?/?$", "", d, flags=re.I) or doi


def doi_key(doi):
    """判重用的 DOI：规范化，预印本平台的版本后缀不计。"""
    d = norm_doi(doi)
    m = PREPRINT_VERSION_RE.match(d) if d else None
    return m.group(1) if m else d


def short_authors(names, n_authors=None):
    """证据表与候选表的作者写法：前 3 位，超过 3 位加 et al.（与 authors.py 的约定相同）。"""
    if not names:
        return ""
    total = n_authors if n_authors is not None else len(names)
    return "; ".join(names[:3]) + (" et al." if total > 3 else "")


def build(members, recs, roots_id, rules, source_order):
    """一组原始记录（recs 的下标 members）→ 合并记录。recs 中每条另有 _ref（出处）与 _order（排序键）。"""
    rs = sorted((recs[i] for i in members), key=lambda r: r["_order"])
    dois, arxivs = [], []
    for r in rs:
        if r["doi"] and r["doi"].lower() not in {d.lower() for d in dois}:
            dois.append(r["doi"])
        if r["arxiv_id"] and r["arxiv_id"].lower() not in {a.lower() for a in arxivs}:
            arxivs.append(r["arxiv_id"])
    journal_dois = [d for d in dois if not ARXIV_DOI_RE.match(d)]
    doi = first(journal_dois) or first(dois)
    arxiv_id = first(arxivs)

    def redundant(d):  # arXiv DOI 与 arxiv_id 指向同一预印本时不重复列出
        m = ARXIV_DOI_RE.match(d)
        return bool(m and arxiv_id and m.group(1).lower() == arxiv_id.lower())

    alt_ids = [f"doi:{d}" for d in dois if d != doi and not redundant(d)]
    alt_ids += [f"arxiv:{a}" for a in arxivs if a != arxiv_id]
    venues = [r["venue"] for r in rs if r["venue"]]
    years = [r["year"] for r in rs if r["year"]]
    abstracts = [r["abstract"] for r in rs if r["abstract"]]
    status = "DOI" if journal_dois else ("arXiv" if (arxiv_id or dois) else "UNVERIFIED")
    sources = sorted({r["source_api"] for r in rs}, key=source_order.index)
    query_ids = sorted({r["query_id"] for r in rs}, key=qnum)
    raw_refs = [r["_ref"] for r in rs]
    best = list_ranks(raw_refs)
    x = {
        "title": first(r["title"] for r in rs),
        "year": min(years) if years else None,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "venue": first(v for v in venues if "arxiv" not in v.lower()) or first(venues),
        "abstract": max(abstracts, key=len) if abstracts else None,
        "id_status": status,
        "alt_ids": alt_ids,
        "title_linked": len({roots_id[i] for i in members}) > 1,
        "sources": sources,
        "query_ids": query_ids,
        "n_queries": len(query_ids),
        "n_sources": len(sources),
        "hits": len(best),
        "mean_rank": round(sum(best.values()) / len(best), 2),
        "raw_refs": raw_refs,
    }
    # 正式发表版本优先作主 DOI；year 取正式发表版本的年份，year_first 取最早年份
    pub = [d for d in dict.fromkeys(r["doi"] for r in rs if r["doi"]) if not rules.preprint_doi.match(norm_doi(d))]
    if pub and pub[0] != x["doi"]:
        old = x["doi"]
        x["doi"] = pub[0]
        x["alt_ids"] = [a for a in x["alt_ids"] if a.lower() != f"doi:{pub[0]}".lower()] + ([f"doi:{old}"] if old else [])
    x["year_first"] = min(years) if years else None
    same = []
    if x["doi"] and not rules.preprint_doi.match(norm_doi(x["doi"])):
        # 带正式发表 DOI 的记录：同时带 arXiv ID 的记录是预印本与正式版合成的一条，年份可能取自预印本
        # （S2 常见，如 Science Advances 2024 的论文记为 2023）；所以先取不带 arXiv ID 的记录的最早年份，
        # 没有这样的记录时取 OpenAlex 的年份（按正式发表），再不行取这些记录的最早年份
        same = [r for r in rs if r["doi"] and norm_doi(r["doi"]) == norm_doi(x["doi"]) and r["year"]]
        plain = [r["year"] for r in same if not r["arxiv_id"]]
        oa = [r["year"] for r in same if r["source_api"] == "openalex"]
        x["year"] = min(plain or oa or [r["year"] for r in same] or years or [None])
    with_authors = next((r for r in rs if r.get("authors")), None)
    x["authors"] = list(with_authors["authors"]) if with_authors else None
    x["n_authors"] = with_authors.get("n_authors") if with_authors else None
    x["field_source"] = _field_source(x, rs, same, with_authors)
    return x


def _field_source(x, rs, same, with_authors):
    def ref(pred):
        r = next((r for r in rs if pred(r)), None)
        return r["_ref"] if r else None
    return {
        "title": ref(lambda r: r["title"]),
        "year": ref(lambda r: r in same and r["year"] == x["year"]) or ref(lambda r: r["year"] and r["year"] == x["year"]),
        "doi": ref(lambda r: r["doi"] and x["doi"] and r["doi"].lower() == x["doi"].lower()),
        "arxiv_id": ref(lambda r: r["arxiv_id"] and x["arxiv_id"] and r["arxiv_id"].lower() == x["arxiv_id"].lower()),
        "venue": ref(lambda r: r["venue"] and r["venue"] == x["venue"]),
        "abstract": ref(lambda r: r["abstract"] and r["abstract"] == x["abstract"]),
        "authors": with_authors["_ref"] if with_authors else None,
    }
