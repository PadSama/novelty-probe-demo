#!/usr/bin/env python3
"""novelty-probe 合并去重脚本。

读取 results/raw/*.json（scripts/search.py 的输出），合并去重，统计每篇的命中情况，输出：
  results/merged/merged.json     去重后的全部文献（含命中统计）
  results/merged/candidates.csv  按命中次数降序的前 20 篇

判定为同一篇的规则（满足任一条即可，用并查集传递）：
  1. DOI 相同（不区分大小写；预印本平台 OSF / TechRxiv / Research Square 的版本后缀 _vN、/vN 忽略不计，
     同一预印本的不同版本视为同一篇）；
  2. arXiv ID 相同（不含版本号）；
  3. 规范化标题相同：去 HTML 标签、转小写、只留字母数字，且至少 5 个词（避免 "Editorial" 这类短标题误并）。
  例如：S2 记录同时有期刊 DOI 和 arXiv ID，OpenAlex 记录只有 arXiv DOI，两者通过 arXiv ID 并成一篇。

命中统计：
  n_queries   命中的检索式数
  n_sources   命中的来源数
  hits        命中次数 = 命中的"检索式 × 来源"结果列表数（最多 6 × 2 = 12）；
              同一列表里出现同一篇的多个版本只算一次
  mean_rank   在各命中列表中最好名次的平均值，越小越靠前（OpenAlex 名次按相关度，S2 名次按被引次数）
candidates.csv 的排序：hits 降序 → n_queries 降序 → n_sources 降序 → mean_rank 升序 → merged_id，取前 20。
  CSV 用带 BOM 的 UTF-8 编码，Excel 可直接打开。

merged.json 中每篇记录的字段：
  merged_id     M001 起编号；按命中检索式数、来源数（多者在前）、年份（新者在前）、标题排序
  title         第一个非空标题（来源顺序 OpenAlex → S2，同一来源内按检索式编号与名次）
  year          组内最早年份（预印本与正式版本可能相差一两年）
  doi           优先取非 arXiv 的 DOI（10.48550/arXiv.* 视为 arXiv 版本）
  arxiv_id      第一个非空 arXiv ID
  venue         第一个非 arXiv 的期刊/会议名，没有才用 arXiv
  abstract      组内最长的一份摘要
  id_status     DOI / arXiv / UNVERIFIED（既无 DOI 也无 arXiv ID，PROJECT.md 规则 b）
  alt_ids       组内其他标识符，如同一研究的另一个 DOI
  title_linked  true 表示这一组只靠标题相同才并到一起，建议人工核对
  sources, query_ids                     命中的来源、检索式
  n_queries, n_sources, hits, mean_rank  见上
  raw_refs      出处 {source}_{query_id}#{名次}，可回查 results/raw/ 中的原始记录
所有值都取自 results/raw/，不补写、不改写；规范化只用于比较。

用法：python3 scripts/merge.py
"""
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "results" / "raw"
OUT_FILE = ROOT / "results" / "merged" / "merged.json"
CANDIDATES_FILE = ROOT / "results" / "merged" / "candidates.csv"
TOP_K = 20
SOURCE_ORDER = ["openalex", "semanticscholar"]
MIN_TITLE_WORDS = 5
ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.I)
# 预印本平台的版本 DOI，如 10.31234/osf.io/abcde_v2、10.36227/techrxiv.123.456/v1、10.21203/rs.3.rs-123/v1
PREPRINT_VERSION_RE = re.compile(r"^(10\.\d+/(?:osf\.io/\w+?|techrxiv\.[\d.]+|rs\.\d+\.rs-\d+))[_/]v\d+$", re.I)
CSV_COLUMNS = ["rank", "merged_id", "hits", "n_queries", "n_sources", "mean_rank", "query_ids", "sources",
               "id_status", "doi", "arxiv_id", "title", "year", "venue", "title_linked", "raw_refs", "abstract"]


def doi_key(doi):
    d = doi.strip().lower()
    m = PREPRINT_VERSION_RE.match(d)
    return m.group(1) if m else d


def qnum(qid):
    return int(re.sub(r"\D", "", qid) or 0)


def first(values):
    return next((v for v in values if v), None)


def norm_title(title):
    if not title:
        return None
    words = re.findall(r"\w+", re.sub(r"<[^>]+>", " ", title).lower())
    return " ".join(words) if len(words) >= MIN_TITLE_WORDS else None


def list_ranks(raw_refs):
    """{结果列表: 该篇在列表中的最好名次}；raw_refs 形如 openalex_Q1#8。"""
    best = {}
    for ref in raw_refs:
        lst, rank = ref.rsplit("#", 1)
        best[lst] = min(best.get(lst, int(rank)), int(rank))
    return best


def load_raw():
    recs, inputs = [], []
    for path in sorted(RAW_DIR.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        m = d["meta"]
        inputs.append({"file": str(path.relative_to(ROOT)),
                       **{k: m.get(k) for k in ("source_api", "query_id", "conversion", "sort",
                                                 "total_hits", "returned", "retrieved_at")}})
        for rank, r in enumerate(d["records"], 1):
            recs.append({**r, "_ref": f"{m['source_api']}_{m['query_id']}#{rank}",
                         "_order": (SOURCE_ORDER.index(m["source_api"]), qnum(m["query_id"]), rank)})
    return recs, inputs


def group(recs, use_title):
    """并查集：返回每条记录所属组的根。use_title=False 时只按 DOI / arXiv ID 判重。"""
    parent = list(range(len(recs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, r in enumerate(recs):
        keys = []
        if r["doi"]:
            keys.append(("doi", doi_key(r["doi"])))
        if r["arxiv_id"]:
            keys.append(("arxiv", r["arxiv_id"].strip().lower()))
        if use_title and norm_title(r["title"]):
            keys.append(("title", norm_title(r["title"])))
        for k in keys:
            if k in seen:
                a, b = find(seen[k]), find(i)
                if a != b:
                    parent[max(a, b)] = min(a, b)
            else:
                seen[k] = i
    return [find(i) for i in range(len(recs))]


def build(members, recs, roots_id):
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
    if journal_dois:
        status = "DOI"
    elif arxiv_id or dois:
        status = "arXiv"
    else:
        status = "UNVERIFIED"
    sources = sorted({r["source_api"] for r in rs}, key=SOURCE_ORDER.index)
    query_ids = sorted({r["query_id"] for r in rs}, key=qnum)
    raw_refs = [r["_ref"] for r in rs]
    best = list_ranks(raw_refs)
    return {
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


def candidate_key(x):
    best = list_ranks(x["raw_refs"])  # 用精确均值排序，mean_rank 字段只是四舍五入后的显示值
    return (-x["hits"], -x["n_queries"], -x["n_sources"], sum(best.values()) / len(best), x["merged_id"])


def write_candidates(candidates):
    with CANDIDATES_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for rank, x in enumerate(candidates, 1):
            w.writerow({
                "rank": rank, "merged_id": x["merged_id"], "hits": x["hits"],
                "n_queries": x["n_queries"], "n_sources": x["n_sources"], "mean_rank": x["mean_rank"],
                "query_ids": ";".join(x["query_ids"]), "sources": ";".join(x["sources"]),
                "id_status": x["id_status"], "doi": x["doi"] or "", "arxiv_id": x["arxiv_id"] or "",
                "title": x["title"] or "", "year": x["year"] or "", "venue": x["venue"] or "",
                "title_linked": "true" if x["title_linked"] else "false",
                "raw_refs": ";".join(x["raw_refs"]), "abstract": x["abstract"] or "",
            })


def main():
    recs, inputs = load_raw()
    if not recs:
        sys.exit("results/raw/ 中没有记录")
    methods = {}
    for inp in inputs:
        methods.setdefault(inp["source_api"], set()).add(inp["conversion"])
    mixed = {s: sorted(c) for s, c in methods.items() if len(c) > 1}
    if mixed:
        sys.exit(f"results/raw/ 中同一来源混有不同检索方式的结果，请先重跑 search.py：{mixed}")

    roots_id = group(recs, use_title=False)
    roots_all = group(recs, use_title=True)
    groups = {}
    for i, root in enumerate(roots_all):
        groups.setdefault(root, []).append(i)

    merged = [build(m, recs, roots_id) for m in groups.values()]
    merged.sort(key=lambda x: (-len(x["query_ids"]), -len(x["sources"]), -(x["year"] or 0),
                               (x["title"] or "").lower()))
    merged = [{"merged_id": f"M{i:03d}", **x} for i, x in enumerate(merged, 1)]

    ranked = sorted(merged, key=candidate_key)
    candidates = ranked[:TOP_K]
    hits_dist = Counter(x["hits"] for x in merged)
    cutoff = candidates[-1]["hits"]
    tied_total = hits_dist[cutoff]
    tied_out = tied_total - sum(x["hits"] == cutoff for x in candidates)
    cand_per_query = Counter(q for x in candidates for q in x["query_ids"])

    qids = sorted({r["query_id"] for r in recs}, key=qnum)
    counts = {
        "raw_records": len(recs),
        "merged_records": len(merged),
        "duplicates_removed": len(recs) - len(merged),
        "title_linked_groups": sum(x["title_linked"] for x in merged),
        "in_multiple_queries": sum(len(x["query_ids"]) > 1 for x in merged),
        "id_status": dict(Counter(x["id_status"] for x in merged)),
        "sources": dict(Counter("+".join(x["sources"]) for x in merged)),
        "per_query": {q: sum(q in x["query_ids"] for x in merged) for q in qids},
        "hits_distribution": {str(h): hits_dist[h] for h in sorted(hits_dist, reverse=True)},
    }
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/merge.py",
        "dedup_rules": ["same DOI (case-insensitive; OSF/TechRxiv/Research Square version suffix ignored)",
                        "same arXiv ID (version stripped)",
                        f"same normalized title (>= {MIN_TITLE_WORDS} words)"],
        "inputs": inputs,
        "counts": counts,
        "candidates": {
            "file": str(CANDIDATES_FILE.relative_to(ROOT)),
            "top_k": TOP_K,
            "sort": "hits desc, n_queries desc, n_sources desc, mean_rank asc, merged_id",
            "cutoff_hits": cutoff,
            "works_with_cutoff_hits": tied_total,
            "of_which_outside_top_k": tied_out,
            "per_query": {q: cand_per_query[q] for q in qids},
        },
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({"meta": meta, "records": merged}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    write_candidates(candidates)

    st, src = counts["id_status"], counts["sources"]
    print(f"inputs:     {len(inputs)} files, {counts['raw_records']} raw records")
    print(f"merged:     {counts['merged_records']} works (duplicates removed: {counts['duplicates_removed']}; "
          f"groups linked by title only: {counts['title_linked_groups']})")
    print(f"id_status:  DOI {st.get('DOI', 0)} | arXiv {st.get('arXiv', 0)} | UNVERIFIED {st.get('UNVERIFIED', 0)}")
    print(f"sources:    openalex only {src.get('openalex', 0)} | semanticscholar only {src.get('semanticscholar', 0)} | "
          f"both {src.get('openalex+semanticscholar', 0)}")
    print("per query:  " + " | ".join(f"{q} {n}" for q, n in counts["per_query"].items())
          + f"   (works hit by more than one query: {counts['in_multiple_queries']})")
    print("hits:       " + " | ".join(f"{h} hit(s): {n} works" for h, n in counts["hits_distribution"].items())
          + "   (hits = number of query x source result lists containing the work)")
    print(f"written:    {OUT_FILE.relative_to(ROOT)}, {CANDIDATES_FILE.relative_to(ROOT)} (top {len(candidates)})")
    if len(ranked) > TOP_K:
        print(f"cutoff:     #{len(candidates)} has hits={cutoff}; {tied_total} works have hits={cutoff}, "
              f"{tied_out} of them fall outside the top {TOP_K} (decided by n_queries, n_sources, mean_rank)")
    print("candidates per query: " + " | ".join(f"{q} {cand_per_query[q]}" for q in qids))
    print(f"\n{'rank':>4}  {'id':<5} {'hits':>4} {'nq':>3} {'ns':>3} {'mean_rank':>9}  {'identifier':<42} title")
    for rank, x in enumerate(candidates, 1):
        ident = (f"doi:{x['doi']}" if x["doi"] else f"arXiv:{x['arxiv_id']}" if x["arxiv_id"] else "UNVERIFIED")
        title = (x["title"] or "")[:60] + ("…" if len(x["title"] or "") > 60 else "")
        print(f"{rank:>4}  {x['merged_id']:<5} {x['hits']:>4} {x['n_queries']:>3} {x['n_sources']:>3} "
              f"{x['mean_rank']:>9}  {ident[:42]:<42} {title}")


if __name__ == "__main__":
    main()
