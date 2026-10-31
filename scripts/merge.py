#!/usr/bin/env python3
"""novelty-probe 合并去重脚本。

读取 results/raw/*.json（scripts/search.py 的输出），合并去重后写入 results/merged/merged.json。

判定为同一篇的规则（满足任一条即可，用并查集传递）：
  1. DOI 相同（不区分大小写；预印本平台 OSF / TechRxiv / Research Square 的版本后缀 _vN、/vN 忽略不计，
     同一预印本的不同版本视为同一篇）；
  2. arXiv ID 相同（不含版本号）；
  3. 规范化标题相同：去 HTML 标签、转小写、只留字母数字，且至少 5 个词（避免 "Editorial" 这类短标题误并）。
  例如：S2 记录同时有期刊 DOI 和 arXiv ID，OpenAlex 记录只有 arXiv DOI，两者通过 arXiv ID 并成一篇。

合并后每篇记录的字段：
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
  sources       命中的来源
  query_ids     命中的检索式
  raw_refs      出处 {source}_{query_id}#{名次}，可回查 results/raw/ 中的原始记录
所有值都取自 results/raw/，不补写、不改写；规范化只用于比较。

用法：python3 scripts/merge.py
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "results" / "raw"
OUT_FILE = ROOT / "results" / "merged" / "merged.json"
SOURCE_ORDER = ["openalex", "semanticscholar"]
MIN_TITLE_WORDS = 5
ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.I)
# 预印本平台的版本 DOI，如 10.31234/osf.io/abcde_v2、10.36227/techrxiv.123.456/v1、10.21203/rs.3.rs-123/v1
PREPRINT_VERSION_RE = re.compile(r"^(10\.\d+/(?:osf\.io/\w+?|techrxiv\.[\d.]+|rs\.\d+\.rs-\d+))[_/]v\d+$", re.I)


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
        "sources": sorted({r["source_api"] for r in rs}, key=SOURCE_ORDER.index),
        "query_ids": sorted({r["query_id"] for r in rs}, key=qnum),
        "raw_refs": [r["_ref"] for r in rs],
    }


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
    }
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/merge.py",
        "dedup_rules": ["same DOI (case-insensitive; OSF/TechRxiv/Research Square version suffix ignored)",
                        "same arXiv ID (version stripped)",
                        f"same normalized title (>= {MIN_TITLE_WORDS} words)"],
        "inputs": inputs,
        "counts": counts,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({"meta": meta, "records": merged}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    st, src = counts["id_status"], counts["sources"]
    print(f"inputs:    {len(inputs)} files, {counts['raw_records']} raw records")
    print(f"merged:    {counts['merged_records']} works (duplicates removed: {counts['duplicates_removed']}; "
          f"groups linked by title only: {counts['title_linked_groups']})")
    print(f"id_status: DOI {st.get('DOI', 0)} | arXiv {st.get('arXiv', 0)} | UNVERIFIED {st.get('UNVERIFIED', 0)}")
    print(f"sources:   openalex only {src.get('openalex', 0)} | semanticscholar only {src.get('semanticscholar', 0)} | "
          f"both {src.get('openalex+semanticscholar', 0)}")
    print("per query: " + " | ".join(f"{q} {n}" for q, n in counts["per_query"].items())
          + f"   (works hit by more than one query: {counts['in_multiple_queries']})")
    print(f"written:   {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
