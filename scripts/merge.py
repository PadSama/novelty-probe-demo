#!/usr/bin/env python3
"""novelty-probe 合并去重脚本。

读取 results/raw/ 中 scripts/search.py 的输出（{source}_{query_id}{suffix}.json），合并去重，
统计每篇的命中情况，输出：
  results/merged/merged{suffix}.json     去重后的全部文献（含命中统计）
  results/merged/candidates{suffix}.csv  按命中次数降序的前 20 篇
只读取后缀与 --suffix 完全相同的文件（默认无后缀即 v1；--suffix _v2 只读 v2），不同版本不会混在一起。

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
  raw_refs      出处 {source}_{query_id}{suffix}#{名次}，可回查 results/raw/ 中的原始记录
所有值都取自 results/raw/，不补写、不改写；规范化只用于比较。

用法：python3 scripts/merge.py [--suffix _v2]
"""
import argparse
import csv
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe.paths import rel as _rel
from novelty_probe.io import configure_console, load_json_lenient, write_json

from search import parse_query
from textmatch import BM25, PREPRINT_DOI_RE, Doc, norm_doi, query_match, version_decision, version_summary

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "results" / "raw"
OUT_DIR = ROOT / "results" / "merged"
TOP_K = 20
SOURCE_ORDER = ["openalex", "semanticscholar"]
MIN_TITLE_WORDS = 5
ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.I)
# 预印本平台的版本 DOI，如 10.31234/osf.io/abcde_v2、10.36227/techrxiv.123.456/v1、10.21203/rs.3.rs-123/v1
PREPRINT_VERSION_RE = re.compile(r"^(10\.\d+/(?:osf\.io/\w+?|techrxiv\.[\d.]+|rs\.\d+\.rs-\d+))[_/]v\d+$", re.I)
CSV_COLUMNS = ["rank", "merged_id", "hits", "n_queries", "n_sources", "mean_rank", "query_ids", "sources",
               "id_status", "doi", "arxiv_id", "title", "year", "venue", "title_linked", "raw_refs", "abstract"]
RRF_K = 60
CSV_COLUMNS_RANKED = ["rank", "merged_id", "rrf", "bm25", "n_conform", "hits", "n_queries", "n_sources", "mean_rank",
                      "query_ids", "sources", "id_status", "doi", "arxiv_id", "title", "year", "year_first", "venue",
                      "title_linked", "review", "raw_refs", "abstract"]


def rel(path):
    """项目内的路径显示为相对路径（正斜杠），项目外的显示为绝对路径。"""
    return _rel(path, ROOT)


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


def raw_files(suffix=""):
    """results/raw/ 中后缀与 suffix 完全相同的 search.py 输出文件。"""
    pattern = re.compile(rf"^(?:{'|'.join(SOURCE_ORDER)})_Q\d+{re.escape(suffix)}\.json$")
    return [p for p in sorted(RAW_DIR.glob("*.json")) if pattern.match(p.name)]


def load_raw(suffix=""):
    recs, inputs = [], []
    for path in raw_files(suffix):
        d = load_json_lenient(path)
        m = d["meta"]
        inputs.append({"file": rel(path),
                       **{k: m.get(k) for k in ("source_api", "query_id", "conversion", "sort",
                                                 "total_hits", "returned", "retrieved_at")}})
        for rank, r in enumerate(d["records"], 1):
            recs.append({**r, "_ref": f"{m['source_api']}_{m['query_id']}{suffix}#{rank}",
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


def write_candidates(candidates, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
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


# ---------- 默认方法：版本识别、正式发表年份、RRF 排序 ----------

def clean_doi(doi):
    """显示用的 DOI：去掉误入 DOI 字段的 URL 查询串与落地页后缀（如 /full/html?utm_source=…），保留大小写。"""
    if not doi:
        return doi
    d = re.split(r"[?#]", doi.strip())[0]
    return re.sub(r"/(?:full|abstract|pdf|epdf|html)(?:/html)?/?$", "", d, flags=re.I) or doi


def ranked_doi_key(doi):
    d = norm_doi(doi)
    m = PREPRINT_VERSION_RE.match(d) if d else None
    return m.group(1) if m else d


def id_roots(recs):
    """并查集：按 DOI（规范化）与 arXiv ID 判重，返回每条记录所属组的根。"""
    parent = list(range(len(recs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, r in enumerate(recs):
        keys = ([("doi", ranked_doi_key(r["doi"]))] if r["doi"] else []) + \
               ([("arxiv", r["arxiv_id"].strip().lower())] if r["arxiv_id"] else [])
        for k in keys:
            if k in seen:
                a, b = find(seen[k]), find(i)
                if a != b:
                    parent[max(a, b)] = min(a, b)
            else:
                seen[k] = i
    return [find(i) for i in range(len(recs))]


def link_versions(recs, roots):
    """在 DOI / arXiv ID 分组之间按 textmatch.version_decision 识别同一研究的不同版本。
    返回 (每条记录的最终根, 合并记录 [(根a, 根b, 原因)], 待核对 [(根a, 根b, 原因)])。"""
    members = {}
    for i, r in enumerate(roots):
        members.setdefault(r, []).append(i)
    summ = {r: version_summary([recs[i] for i in idx]) for r, idx in members.items()}
    parent = {r: r for r in members}

    def find(r):
        while parent[r] != r:
            parent[r] = parent[parent[r]]
            r = parent[r]
        return r

    merges, reviews = [], []
    for a, b in combinations(sorted(members), 2):
        decision, reason = version_decision(summ[a], summ[b])
        if decision == "merge":
            merges.append((a, b, reason))
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
        elif decision == "review":
            reviews.append((a, b, reason))
    final = [find(r) for r in roots]
    reviews = [(a, b, why) for a, b, why in reviews if find(a) != find(b)]
    return final, merges, reviews


def build_ranked(members, recs, roots_id):
    """在 build() 的基础上：正式发表版本优先作主 DOI；year 取正式发表版本的年份，year_first 取最早年份。"""
    x = build(members, recs, roots_id)
    rs = sorted((recs[i] for i in members), key=lambda r: r["_order"])
    dois = list(dict.fromkeys(r["doi"] for r in rs if r["doi"]))
    pub = [d for d in dois if not PREPRINT_DOI_RE.match(norm_doi(d))]
    if pub and pub[0] != x["doi"]:
        old = x["doi"]
        x["doi"] = pub[0]
        x["alt_ids"] = [a for a in x["alt_ids"] if a.lower() != f"doi:{pub[0]}".lower()] + ([f"doi:{old}"] if old else [])
    years = [r["year"] for r in rs if r["year"]]
    x["year_first"] = min(years) if years else None
    if x["doi"] and not PREPRINT_DOI_RE.match(norm_doi(x["doi"])):
        # 带正式发表 DOI 的记录：同时带 arXiv ID 的记录是预印本与正式版合成的一条，年份可能取自预印本
        # （S2 常见，如 Science Advances 2024 的论文记为 2023）；所以先取不带 arXiv ID 的记录的最早年份，
        # 没有这样的记录时取 OpenAlex 的年份（按正式发表），再不行取这些记录的最早年份
        same = [r for r in rs if r["doi"] and norm_doi(r["doi"]) == norm_doi(x["doi"]) and r["year"]]
        plain = [r["year"] for r in same if not r["arxiv_id"]]
        oa = [r["year"] for r in same if r["source_api"] == "openalex"]
        x["year"] = min(plain or oa or [r["year"] for r in same] or years or [None])
    return x


def load_queries_from_raw(suffix):
    """各结果文件 meta 中的原检索式：{query_id: (包含组, 排除组)}。"""
    out = {}
    for path in raw_files(suffix):
        m = load_json_lenient(path)["meta"]
        out.setdefault(m["query_id"], parse_query(m["query_original"]))
    return out


def merge_ranked(recs, suffix):
    for r in recs:
        r["doi"] = clean_doi(r["doi"])
    roots_id = id_roots(recs)
    roots_all, merges, reviews = link_versions(recs, roots_id)
    groups = {}
    for i, root in enumerate(roots_all):
        groups.setdefault(root, []).append(i)
    built = {root: build_ranked(m, recs, roots_id) for root, m in groups.items()}
    order = sorted(built, key=lambda r: (-len(built[r]["query_ids"]), -len(built[r]["sources"]),
                                         -(built[r]["year"] or 0), (built[r]["title"] or "").lower()))
    mid = {root: f"M{i:03d}" for i, root in enumerate(order, 1)}
    for root, x in built.items():
        x["review"] = []
    for a, b, why in reviews:
        ra, rb = roots_all[a], roots_all[b]
        built[ra]["review"].append({"with": mid[rb], "reason": why})
        built[rb]["review"].append({"with": mid[ra], "reason": why})

    queries = load_queries_from_raw(suffix)
    terms = list(dict.fromkeys(t for inc, _ in queries.values() for g in inc for t in g))
    ignore = list(dict.fromkeys(t for _, exc in queries.values() for g in exc for t in g))
    merged = [{"merged_id": mid[root], **built[root]} for root in order]
    docs = [Doc(x["title"], x["abstract"]) for x in merged]
    bm = BM25(docs, terms)
    for i, (x, d) in enumerate(zip(merged, docs)):
        x["rrf"] = round(sum(1 / (RRF_K + r) for r in list_ranks(x["raw_refs"]).values()), 6)
        x["bm25"] = round(bm.score(i, ignore), 3)
        x["n_conform"] = sum(query_match(inc, d, exc, ignore) for inc, exc in queries.values())
    info = {
        "version_links": [{"records": [recs[a]["_ref"], recs[b]["_ref"]], "merged_id": mid[roots_all[a]], "reason": why}
                          for a, b, why in merges],
        "review_pairs": [{"merged_ids": [mid[roots_all[a]], mid[roots_all[b]]], "reason": why} for a, b, why in reviews],
        "bm25_terms": terms, "ignored_phrases": ignore,
    }
    return merged, info


def review_clusters(pairs):
    """把两两的待核对关系并成组，便于显示：[(merged_id 列表, 原因列表)]。"""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in pairs:
        a, b = (find(m) for m in p["merged_ids"])
        if a != b:
            parent[max(a, b)] = min(a, b)
    clusters = {}
    for p in pairs:
        c = clusters.setdefault(find(p["merged_ids"][0]), [set(), []])
        c[0].update(p["merged_ids"])
        if p["reason"] not in c[1]:
            c[1].append(p["reason"])
    return [(sorted(ids), reasons) for ids, reasons in sorted(clusters.values(), key=lambda c: min(c[0]))]


def write_candidates_ranked(candidates, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS_RANKED)
        w.writeheader()
        for rank, x in enumerate(candidates, 1):
            w.writerow({
                "rank": rank, "merged_id": x["merged_id"], "rrf": x["rrf"], "bm25": x["bm25"], "n_conform": x["n_conform"],
                "hits": x["hits"], "n_queries": x["n_queries"], "n_sources": x["n_sources"], "mean_rank": x["mean_rank"],
                "query_ids": ";".join(x["query_ids"]), "sources": ";".join(x["sources"]),
                "id_status": x["id_status"], "doi": x["doi"] or "", "arxiv_id": x["arxiv_id"] or "",
                "title": x["title"] or "", "year": x["year"] or "", "year_first": x["year_first"] or "",
                "venue": x["venue"] or "", "title_linked": "true" if x["title_linked"] else "false",
                "review": "; ".join(f"{v['with']}: {v['reason']}" for v in x["review"]),
                "raw_refs": ";".join(x["raw_refs"]), "abstract": x["abstract"] or "",
            })


def main():
    configure_console()
    ap = argparse.ArgumentParser(description="Merge and dedupe search results; write top candidates.")
    ap.add_argument("--suffix", default="", help="只处理这个后缀的结果文件，如 _v2（默认无后缀，即 v1）")
    ap.add_argument("--legacy", action="store_true",
                    help="用 Step 6 / Step 14 当时的方法（按命中次数排序、只按完全相同的标题合并），复现已提交的 v1、v2 结果")
    args = ap.parse_args()
    out_file = OUT_DIR / f"merged{args.suffix}.json"
    cand_file = OUT_DIR / f"candidates{args.suffix}.csv"

    recs, inputs = load_raw(args.suffix)
    if not recs:
        sys.exit(f"results/raw/ 中没有后缀为 '{args.suffix}' 的记录")
    methods = {}
    for inp in inputs:
        methods.setdefault(inp["source_api"], set()).add(inp["conversion"])
    mixed = {s: sorted(c) for s, c in methods.items() if len(c) > 1}
    if mixed:
        sys.exit(f"results/raw/ 中同一来源混有不同检索方式的结果，请先重跑 search.py：{mixed}")
    if not args.legacy:
        return main_ranked(args, recs, inputs, out_file, cand_file)

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
            "file": rel(cand_file),
            "top_k": TOP_K,
            "sort": "hits desc, n_queries desc, n_sources desc, mean_rank asc, merged_id",
            "cutoff_hits": cutoff,
            "works_with_cutoff_hits": tied_total,
            "of_which_outside_top_k": tied_out,
            "per_query": {q: cand_per_query[q] for q in qids},
        },
    }
    write_json(out_file, {"meta": meta, "records": merged})
    write_candidates(candidates, cand_file)

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
    print(f"written:    {rel(out_file)}, {rel(cand_file)} (top {len(candidates)})")
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


def main_ranked(args, recs, inputs, out_file, cand_file):
    merged, info = merge_ranked(recs, args.suffix)
    ranked = sorted(merged, key=lambda x: (-x["rrf"], -x["bm25"], x["merged_id"]))
    candidates = ranked[:TOP_K]
    cut = candidates[-1]
    tied_at_cut = sum(1 for x in merged if (x["rrf"], x["bm25"]) == (cut["rrf"], cut["bm25"]))
    qids = sorted({r["query_id"] for r in recs}, key=qnum)
    cand_per_query = Counter(q for x in candidates for q in x["query_ids"])
    counts = {
        "raw_records": len(recs),
        "merged_records": len(merged),
        "duplicates_removed": len(recs) - len(merged),
        "title_linked_groups": sum(x["title_linked"] for x in merged),
        "review_pairs": len(info["review_pairs"]),
        "in_multiple_queries": sum(len(x["query_ids"]) > 1 for x in merged),
        "id_status": dict(Counter(x["id_status"] for x in merged)),
        "sources": dict(Counter("+".join(x["sources"]) for x in merged)),
        "per_query": {q: sum(q in x["query_ids"] for x in merged) for q in qids},
        "hits_distribution": {str(h): n for h, n in sorted(Counter(x["hits"] for x in merged).items(), reverse=True)},
    }
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/merge.py",
        "method": "default (version linking, version-of-record year, RRF ranking); --legacy reproduces Steps 6/14",
        "dedup_rules": ["same DOI (normalized: case, URL query and landing-page suffix ignored; "
                        "OSF/TechRxiv/Research Square version suffix ignored)",
                        "same arXiv ID (version stripped)",
                        "versions of one work: same normalized title (trailing publication-status notes stripped, "
                        ">= 5 words), no notice/variant word on one side only, no two different non-preprint DOIs, "
                        "no data-repository DOI, year gap <= 3, abstract word Jaccard >= 0.5 when both have abstracts",
                        "near-identical titles and same-title pairs failing a check are flagged for review, not merged"],
        "year": "year of the version of record (non-preprint DOI; OpenAlex year preferred); year_first = earliest",
        "inputs": inputs,
        "counts": counts,
        **info,
        "candidates": {
            "file": rel(cand_file),
            "top_k": TOP_K,
            "sort": f"RRF over result lists (k={RRF_K}) desc, BM25 over all query terms desc, merged_id",
            "works_tied_with_cutoff": tied_at_cut,
            "per_query": {q: cand_per_query[q] for q in qids},
        },
    }
    write_json(out_file, {"meta": meta, "records": merged})
    write_candidates_ranked(candidates, cand_file)

    st, src = counts["id_status"], counts["sources"]
    print(f"inputs:     {len(inputs)} files, {counts['raw_records']} raw records")
    print(f"merged:     {counts['merged_records']} works (duplicates removed: {counts['duplicates_removed']}; "
          f"groups linked as versions by title: {counts['title_linked_groups']}; pairs flagged for review: "
          f"{counts['review_pairs']} in {len(review_clusters(info['review_pairs']))} cluster(s))")
    for v in info["version_links"]:
        print(f"  version link  {v['merged_id']}: {' + '.join(v['records'])}")
    for ids, reasons in review_clusters(info["review_pairs"]):
        print(f"  review        {', '.join(ids)}: {'; '.join(reasons)}")
    print(f"id_status:  DOI {st.get('DOI', 0)} | arXiv {st.get('arXiv', 0)} | UNVERIFIED {st.get('UNVERIFIED', 0)}")
    print(f"sources:    openalex only {src.get('openalex', 0)} | semanticscholar only {src.get('semanticscholar', 0)} | "
          f"both {src.get('openalex+semanticscholar', 0)}")
    print("per query:  " + " | ".join(f"{q} {n}" for q, n in counts["per_query"].items()))
    print(f"written:    {rel(out_file)}, {rel(cand_file)} (top {len(candidates)}; sorted by RRF, then BM25)")
    print(f"cutoff:     works sharing the #{len(candidates)} score (RRF and BM25): {tied_at_cut}")
    print(f"\n{'rank':>4}  {'id':<5} {'rrf':>7} {'bm25':>6} {'conf':>4} {'hits':>4} {'year':>4}  {'identifier':<40} title")
    for rank, x in enumerate(candidates, 1):
        ident = (f"doi:{x['doi']}" if x["doi"] else f"arXiv:{x['arxiv_id']}" if x["arxiv_id"] else "UNVERIFIED")
        title = (x["title"] or "")[:58] + ("…" if len(x["title"] or "") > 58 else "")
        print(f"{rank:>4}  {x['merged_id']:<5} {x['rrf']:>7.4f} {x['bm25']:>6.2f} {x['n_conform']:>4} {x['hits']:>4} "
              f"{x['year'] or '':>4}  {ident[:40]:<40} {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
