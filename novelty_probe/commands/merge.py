#!/usr/bin/env python3
"""novelty-probe 合并去重脚本。

读取 results/raw/ 中检索命令（novelty-probe search）的输出（{source}_{query_id}{suffix}.json），合并去重，
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

以上是 --legacy（教程 v1、v2 当时的方法）。默认方法（阶段 4 起；实现在 novelty_probe/record.py、dedupe.py、rank.py）：
  去重：每个合并决定记规则编号（D1–D5），疑似重复但保持分开的记原因（R1–R8），见 merged.json 的 meta.dedupe_rules；
        作者参与判断（题目几乎相同且作者有重合时合并；题目相同但作者完全不重合时不合并）；不设人工复核。
  记录另有 year_first、authors、n_authors、field_source（各字段取自哪条原始记录）、dedupe_rules、review（保持分开的疑似重复）、
        rrf、bm25、n_conform；排序：RRF（k=60）降序 → BM25 → merged_id，取前 top_k 篇。
  合并时一起写出：candidates{suffix}.ris（导入文献管理软件）、run_manifest{suffix}.json（运行清单）、
        search_report{suffix}.md（PRISMA-S 风格的检索报告），见 novelty_probe/export.py、report.py。

默认方法的参数来自配置 novelty-probe.json：merge.top_k / rrf_k / bm25.k1 / bm25.b，版本识别 versions.*；
meta 里记录所用参数与 config_hash。--legacy 的方法与参数固定（前 20 篇、标题至少 5 个词），不读配置，只用于复现教程结果。

用法：novelty-probe merge [--suffix _v2] [--root 目录] [--config 文件] [--lang en]
"""
import argparse
import csv
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from novelty_probe.paths import PACKAGE_ROOT
from novelty_probe import config as np_config, dedupe, export, i18n, rank, record, report, runtime
from novelty_probe.sources import NAMES as SOURCE_NAMES
from novelty_probe.i18n import t
from novelty_probe.paths import rel as _rel
from novelty_probe.io import load_json_lenient, write_json, write_text
from novelty_probe.record import ARXIV_DOI_RE, PREPRINT_VERSION_RE, first, list_ranks, qnum

from novelty_probe.commands.search import parse_query
from novelty_probe.text import DEFAULT_RULES, VersionRules

ROOT = PACKAGE_ROOT   # 源码仓库（在仓库里运行时）；其他项目目录由 runtime.bind_root 换成该目录
RAW_DIR = ROOT / "results" / "raw"
OUT_DIR = ROOT / "results" / "merged"
# 默认方法的参数（configure(cfg) 按配置设定；这里是内置默认值）
_M = np_config.DEFAULTS["merge"]
TOP_K = _M["top_k"]
RRF_K = _M["rrf_k"]
BM25_K1, BM25_B = _M["bm25"]["k1"], _M["bm25"]["b"]
RULES = DEFAULT_RULES     # 版本识别（textmatch.VersionRules）
MAX_GROUPS = np_config.DEFAULTS["versions"]["max_cluster_groups"]   # 一个合并组最多含几个标识符分组
# --legacy 的固定参数（复现 Step 6 / Step 14 的结果，不随配置变化）
LEGACY_TOP_K = 20
MIN_TITLE_WORDS = 5
# 来源顺序取自数据源注册表（novelty_probe/sources/）：决定读哪些原始结果文件，以及标题等字段优先取哪个来源的值
SOURCE_ORDER = SOURCE_NAMES     # 注册表里的同一个列表：登记新数据源后立即生效
CSV_COLUMNS = ["rank", "merged_id", "hits", "n_queries", "n_sources", "mean_rank", "query_ids", "sources",
               "id_status", "doi", "arxiv_id", "title", "year", "venue", "title_linked", "raw_refs", "abstract"]
CSV_COLUMNS_RANKED = ["rank", "merged_id", "rrf", "bm25", "n_conform", "hits", "n_queries", "n_sources", "mean_rank",
                      "query_ids", "sources", "id_status", "doi", "arxiv_id", "title", "authors", "year", "year_first",
                      "venue", "title_linked", "review", "raw_refs", "abstract"]


def configure(cfg):
    """按配置设定默认方法的参数（main() 开头调用）。每次调用整体替换。"""
    global TOP_K, RRF_K, BM25_K1, BM25_B, RULES, MAX_GROUPS
    m = cfg["merge"]
    TOP_K, RRF_K = m["top_k"], m["rrf_k"]
    BM25_K1, BM25_B = m["bm25"]["k1"], m["bm25"]["b"]
    RULES = VersionRules.from_config(cfg)
    MAX_GROUPS = cfg["versions"]["max_cluster_groups"]


def rel(path):
    """项目内的路径显示为相对路径（正斜杠），项目外的显示为绝对路径。"""
    return _rel(path, ROOT)


def doi_key(doi):
    """--legacy 的判重键（默认方法用 record.doi_key，先规范化 DOI）。"""
    d = doi.strip().lower()
    m = PREPRINT_VERSION_RE.match(d)
    return m.group(1) if m else d


def norm_title(title):
    if not title:
        return None
    words = re.findall(r"\w+", re.sub(r"<[^>]+>", " ", title).lower())
    return " ".join(words) if len(words) >= MIN_TITLE_WORDS else None


def raw_files(suffix=""):
    """results/raw/ 中后缀与 suffix 完全相同的 search.py 输出文件（各登记数据源的 {来源}_Q<数字>{后缀}.json）。"""
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
# 实现在 novelty_probe/record.py（合并记录）、dedupe.py（去重规则 D1–D5 / R1–R8）、rank.py（RRF 与 BM25）

def load_queries_from_raw(suffix):
    """各结果文件 meta 中的原检索式：{query_id: (包含组, 排除组)}。"""
    out = {}
    for path in raw_files(suffix):
        m = load_json_lenient(path)["meta"]
        out.setdefault(m["query_id"], parse_query(m["query_original"]))
    return out


def merge_ranked(recs, suffix):
    for r in recs:
        r["doi"] = record.clean_doi(r["doi"])
    roots_id, id_links = dedupe.id_groups(recs)
    roots_all, merges, kept = dedupe.link_versions(recs, roots_id, RULES, MAX_GROUPS)
    groups = {}
    for i, root in enumerate(roots_all):
        groups.setdefault(root, []).append(i)
    built = {root: record.build(m, recs, roots_id, RULES, SOURCE_ORDER) for root, m in groups.items()}
    order = sorted(built, key=lambda r: (-len(built[r]["query_ids"]), -len(built[r]["sources"]),
                                         -(built[r]["year"] or 0), (built[r]["title"] or "").lower()))
    mid = {root: f"M{i:03d}" for i, root in enumerate(order, 1)}
    used = dedupe.rules_by_group(roots_all, roots_id, id_links, merges)
    for root, x in built.items():
        x["review"] = []
        x["dedupe_rules"] = used.get(root, [])
    for a, b, rule, why in kept:
        ra, rb = roots_all[a], roots_all[b]
        built[ra]["review"].append({"with": mid[rb], "rule": rule, "reason": why})
        built[rb]["review"].append({"with": mid[ra], "rule": rule, "reason": why})

    queries = load_queries_from_raw(suffix)
    merged = [{"merged_id": mid[root], **built[root]} for root in order]
    terms = rank.score(merged, queries, RRF_K, BM25_K1, BM25_B)
    info = {
        "dedupe_rules": dedupe.RULES,
        "version_links": [{"records": [recs[a]["_ref"], recs[b]["_ref"]], "merged_id": mid[roots_all[a]], "rule": rule,
                           "reason": why} for a, b, rule, why in merges],
        "review_pairs": [{"merged_ids": [mid[roots_all[a]], mid[roots_all[b]]], "rule": rule, "reason": why}
                         for a, b, rule, why in kept],
        **terms,
    }
    counts = {"id_links": dict(sorted(Counter(rule for _, _, rule in id_links).items())),
              "version_links": dict(sorted(Counter(rule for _, _, rule, _ in merges).items())),
              "kept_separate": dict(sorted(Counter(rule for _, _, rule, _ in kept).items()))}
    return merged, info, counts


def review_clusters(pairs):
    """把两两的疑似关系并成组，便于显示：[(merged_id 列表, 原因列表)]。"""
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
        reason = f"{p['rule']} {p['reason']}" if p.get("rule") else p["reason"]
        if reason not in c[1]:
            c[1].append(reason)
    return [(sorted(ids), reasons) for ids, reasons in sorted(clusters.values(), key=lambda c: min(c[0]))]


def write_candidates_ranked(candidates, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS_RANKED)
        w.writeheader()
        for rank_no, x in enumerate(candidates, 1):
            w.writerow({
                "rank": rank_no, "merged_id": x["merged_id"], "rrf": x["rrf"], "bm25": x["bm25"], "n_conform": x["n_conform"],
                "hits": x["hits"], "n_queries": x["n_queries"], "n_sources": x["n_sources"], "mean_rank": x["mean_rank"],
                "query_ids": ";".join(x["query_ids"]), "sources": ";".join(x["sources"]),
                "id_status": x["id_status"], "doi": x["doi"] or "", "arxiv_id": x["arxiv_id"] or "",
                "title": x["title"] or "", "authors": record.short_authors(x.get("authors"), x.get("n_authors")),
                "year": x["year"] or "", "year_first": x["year_first"] or "",
                "venue": x["venue"] or "", "title_linked": "true" if x["title_linked"] else "false",
                "review": "; ".join(f"{v['with']} ({v['rule']}): {v['reason']}" for v in x["review"]),
                "raw_refs": ";".join(x["raw_refs"]), "abstract": x["abstract"] or "",
            })


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Merge and dedupe search results; write top candidates.")
    ap.add_argument("--suffix", default="", help=t("arg.suffix_only"))
    ap.add_argument("--legacy", action="store_true", help=t("merge.arg.legacy"))
    runtime.add_common_args(ap)
    args = ap.parse_args()
    rt = runtime.init(args)
    runtime.bind_root(globals(), rt.root, {"RAW_DIR": "results/raw", "OUT_DIR": "results/merged"})
    configure(rt.cfg)
    args.cfg_meta = np_config.meta(rt.cfg, rel)
    out_file = OUT_DIR / f"merged{args.suffix}.json"
    cand_file = OUT_DIR / f"candidates{args.suffix}.csv"

    recs, inputs = load_raw(args.suffix)
    if not recs:
        sys.exit(t("merge.no_records", suffix=args.suffix))
    methods = {}
    for inp in inputs:
        methods.setdefault(inp["source_api"], set()).add(inp["conversion"])
    mixed = {s: sorted(c) for s, c in methods.items() if len(c) > 1}
    if mixed:
        sys.exit(t("merge.mixed_methods", mixed=mixed))
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
    candidates = ranked[:LEGACY_TOP_K]
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
            "top_k": LEGACY_TOP_K,
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
    if len(ranked) > LEGACY_TOP_K:
        print(f"cutoff:     #{len(candidates)} has hits={cutoff}; {tied_total} works have hits={cutoff}, "
              f"{tied_out} of them fall outside the top {LEGACY_TOP_K} (decided by n_queries, n_sources, mean_rank)")
    print("candidates per query: " + " | ".join(f"{q} {cand_per_query[q]}" for q in qids))
    print(f"\n{'rank':>4}  {'id':<5} {'hits':>4} {'nq':>3} {'ns':>3} {'mean_rank':>9}  {'identifier':<42} title")
    for rank_no, x in enumerate(candidates, 1):
        ident = (f"doi:{x['doi']}" if x["doi"] else f"arXiv:{x['arxiv_id']}" if x["arxiv_id"] else "UNVERIFIED")
        title = (x["title"] or "")[:60] + ("…" if len(x["title"] or "") > 60 else "")
        print(f"{rank_no:>4}  {x['merged_id']:<5} {x['hits']:>4} {x['n_queries']:>3} {x['n_sources']:>3} "
              f"{x['mean_rank']:>9}  {ident[:42]:<42} {title}")
    return 0


def main_ranked(args, recs, inputs, out_file, cand_file):
    merged, info, dedupe_counts = merge_ranked(recs, args.suffix)
    ranked = sorted(merged, key=rank.sort_key)
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
        "dedupe": dedupe_counts,
        "with_authors": sum(1 for x in merged if x.get("authors")),
        "in_multiple_queries": sum(len(x["query_ids"]) > 1 for x in merged),
        "id_status": dict(Counter(x["id_status"] for x in merged)),
        "sources": dict(Counter("+".join(x["sources"]) for x in merged)),
        "per_query": {q: sum(q in x["query_ids"] for x in merged) for q in qids},
        "hits_distribution": {str(h): n for h, n in sorted(Counter(x["hits"] for x in merged).items(), reverse=True)},
    }
    meta = {
        "schema": record.SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/merge.py",
        "method": "default (version linking with author evidence, version-of-record year, RRF ranking); "
                  "--legacy reproduces Steps 6/14",
        "year": "year of the version of record (non-preprint DOI; OpenAlex year preferred); year_first = earliest",
        "parameters": {"top_k": TOP_K, "rrf_k": RRF_K, "bm25": {"k1": BM25_K1, "b": BM25_B},
                       "year_window": RULES.year_window, "min_title_words": RULES.min_title_words,
                       "max_cluster_groups": MAX_GROUPS},
        **getattr(args, "cfg_meta", {}),
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
    # 研究者不用另外运行：候选的 RIS（导入文献管理软件）、运行清单与检索报告随合并一起写出
    ris_file = cand_file.with_suffix(".ris")
    export.write_ris(ris_file, candidates, rules=RULES)
    manifest = report.build_manifest(ROOT, raw_files(args.suffix), meta, [out_file, cand_file, ris_file], candidates)
    manifest_file = OUT_DIR / f"run_manifest{args.suffix}.json"
    report_file = OUT_DIR / f"search_report{args.suffix}.md"
    write_json(manifest_file, manifest)
    write_text(report_file, report.render_report(manifest, args.suffix))

    st, src = counts["id_status"], counts["sources"]
    print(f"inputs:     {len(inputs)} files, {counts['raw_records']} raw records")
    print(f"merged:     {counts['merged_records']} works (duplicates removed: {counts['duplicates_removed']}; "
          f"groups linked as versions by title: {counts['title_linked_groups']}; possible duplicates kept separate: "
          f"{counts['review_pairs']} pair(s) in {len(review_clusters(info['review_pairs']))} cluster(s))")
    print("dedupe:     " + " | ".join(f"{k} {v}" for part in ("id_links", "version_links", "kept_separate")
                                       for k, v in dedupe_counts[part].items()) + "   (rules: merged.json meta.dedupe_rules)")
    for v in info["version_links"]:
        print(f"  version link  {v['merged_id']} ({v['rule']}): {' + '.join(v['records'])}")
    for ids, reasons in review_clusters(info["review_pairs"]):
        print(f"  kept apart    {', '.join(ids)}: {'; '.join(reasons)}")
    print(f"id_status:  DOI {st.get('DOI', 0)} | arXiv {st.get('arXiv', 0)} | UNVERIFIED {st.get('UNVERIFIED', 0)}")
    print(f"sources:    openalex only {src.get('openalex', 0)} | semanticscholar only {src.get('semanticscholar', 0)} | "
          f"both {src.get('openalex+semanticscholar', 0)}")
    print("per query:  " + " | ".join(f"{q} {n}" for q, n in counts["per_query"].items()))
    lm = manifest["counts"]["local_match"]
    if lm:
        print("local match: " + " | ".join(f"{s_}: {v['with_abstract'] - v['conforming']} of {v['with_abstract']} records with an "
                                          f"abstract judged non-conforming locally" for s_, v in lm.items()))
    print(f"authors:    {counts['with_authors']} of {counts['merged_records']} works")
    print(f"written:    {rel(out_file)}, {rel(cand_file)} (top {len(candidates)}; sorted by RRF, then BM25)")
    print(f"            {rel(ris_file)} (RIS for Zotero / EndNote), {rel(manifest_file)}, {rel(report_file)}")
    print(f"cutoff:     works sharing the #{len(candidates)} score (RRF and BM25): {tied_at_cut}")
    print(f"\n{'rank':>4}  {'id':<5} {'rrf':>7} {'bm25':>6} {'conf':>4} {'hits':>4} {'year':>4}  {'identifier':<40} title")
    for rank_no, x in enumerate(candidates, 1):
        ident = (f"doi:{x['doi']}" if x["doi"] else f"arXiv:{x['arxiv_id']}" if x["arxiv_id"] else "UNVERIFIED")
        title = (x["title"] or "")[:58] + ("…" if len(x["title"] or "") > 58 else "")
        print(f"{rank_no:>4}  {x['merged_id']:<5} {x['rrf']:>7.4f} {x['bm25']:>6.2f} {x['n_conform']:>4} {x['hits']:>4} "
              f"{x['year'] or '':>4}  {ident[:40]:<40} {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
