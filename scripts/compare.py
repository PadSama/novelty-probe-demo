#!/usr/bin/env python3
"""比较几轮检索结果：已知文献排在第几、前 K 篇的构成、截断处的并列。用于评估流程改进，也可用于"相对召回"检查。

对每个后缀（如 "" 即 v1、_v1b），读取 results/merged/merged{suffix}.json、candidates{suffix}.csv、
chase_*{suffix}.csv 与 results/raw 中的原检索式，输出：
  known       已知文献（--known 给出的 DOI 或 arXiv:<ID>）在全部合并结果中的名次（按该轮的排序方法），
              以及在各引文追踪列表中的名次；同一研究的其他版本（alt_ids）也算命中
  ties        截断处（第 --top 名）与之并列的篇数
  前 K 篇（K = 10 与 --top）：
    conform   按词干还原判断，至少满足一条检索式的篇数（排除组与 --ignore-phrases 中的短语所覆盖的位置不计）
    noise     只有把 --ignore-phrases 中的短语也算作匹配时才满足检索式的篇数（例如只因 "narrow AI" 命中 narrowing）
    genai     标题或摘要含生成式 AI 关键词的篇数（默认取研究者确定的筛选词：LLM、ChatGPT、Gemini、Claude、OpenAI、
              Anthropic，另加 generative AI、large language model、GPT）
    abstract  有摘要的篇数
    year      年份中位数；2015 年以前的篇数
排序方法：merged.json 的 meta 带 method 字段的按 RRF → BM25 → merged_id（merge.py 默认方法），
否则按命中次数等（merge.py --legacy，即 Step 6 / 14 的方法）。
只读，不联网，不改动任何文件（给了 --out 时只写这个文件）。

用法：
  python3 scripts/compare.py --runs ,_v1b --known 10.1038/s41586-025-09922-y
  python3 scripts/compare.py --runs _v2,_v2b --known 10.1038/s41586-025-09922-y --ignore-phrases '"narrow AI"' '"narrow applications"'
"""
import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

import merge
from textmatch import Doc, norm_doi, query_match, term_in

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results" / "merged"
GENAI_TERMS = ["LLM", "LLMs", "ChatGPT", "GPT", "Gemini", "Claude", "OpenAI", "Anthropic", '"generative AI"',
               '"generative artificial intelligence"', '"large language model"']


def ranked_records(suffix):
    data = json.loads((OUT_DIR / f"merged{suffix}.json").read_text(encoding="utf-8"))
    recs = data["records"]
    if "method" in data["meta"]:
        recs = sorted(recs, key=lambda x: (-x["rrf"], -x["bm25"], x["merged_id"]))
        ties = data["meta"]["candidates"].get("works_tied_with_cutoff")
        method = "RRF"
    else:
        recs = sorted(recs, key=merge.candidate_key)
        ties = data["meta"]["candidates"].get("works_with_cutoff_hits")
        method = "hits (legacy)"
    return recs, ties, method


def identifiers(x):
    ids = set()
    if x.get("doi"):
        ids.add(("doi", norm_doi(x["doi"])))
    if x.get("arxiv_id"):
        ids |= {("arxiv", x["arxiv_id"].lower()), ("doi", f"10.48550/arxiv.{x['arxiv_id']}".lower())}
    for a in x.get("alt_ids") or []:
        kind, _, val = a.partition(":")
        ids.add(("doi", norm_doi(val)) if kind == "doi" else ("arxiv", val.lower()))
    return ids


def known_key(item):
    item = item.strip()
    if item.lower().startswith("arxiv:"):
        return ("arxiv", item.split(":", 1)[1].lower())
    return ("doi", norm_doi(item))


def topk_stats(recs, k, queries, ignore):
    top = recs[:k]
    docs = [Doc(x["title"], x["abstract"]) for x in top]
    exclude_terms = [t for _, exc in queries.values() for g in exc for t in g]
    strict = [any(query_match(inc, d, exc, ignore + exclude_terms) for inc, exc in queries.values()) for d in docs]
    loose = [any(query_match(inc, d, exc) for inc, exc in queries.values()) for d in docs]
    years = [x["year"] for x in top if x.get("year")]
    return {"n": len(top), "conform": sum(strict), "noise": sum(l and not s for l, s in zip(loose, strict)),
            "genai": sum(any(term_in(t, d) for t in GENAI_TERMS) for d in docs),
            "abstract": sum(bool(x["abstract"]) for x in top),
            "year_median": statistics.median(years) if years else None, "before_2015": sum(y < 2015 for y in years)}


def chase_ranks(suffix, expanded):
    """expanded: {已知文献: 它的全部标识符（含合并结果中同一研究其他版本的标识符）}。"""
    out = {}
    for path in sorted(OUT_DIR.glob(f"chase_*{suffix}.csv")):
        label = path.name[len("chase_"):-len(f"{suffix}.csv")]
        if not label or (suffix == "" and "_" in label):
            continue  # 无后缀时跳过其他后缀的文件
        with path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                ids = identifiers({"doi": row["doi"], "arxiv_id": row["arxiv_id"]})
                for k, ks in expanded.items():
                    if ids & ks:
                        out.setdefault(k, []).append(f"{label}/{row['path']} #{row['rank']}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Compare runs: known-item ranks, top-k composition, ties.")
    ap.add_argument("--runs", required=True, help='逗号分隔的后缀，v1 写空字符串，如 ",_v1b"')
    ap.add_argument("--known", default="", help="逗号分隔的已知文献 DOI 或 arXiv:<ID>")
    ap.add_argument("--ignore-phrases", nargs="*", default=[], help='判断 noise 时不计入匹配的短语，如 \'"narrow AI"\'')
    ap.add_argument("--top", type=int, default=merge.TOP_K)
    ap.add_argument("--out", type=Path, help="把结果另存为 JSON")
    args = ap.parse_args()
    runs = args.runs.split(",")
    keys = [known_key(k) for k in args.known.split(",") if k.strip()]
    report = {}
    for suffix in runs:
        name = suffix or "(v1)"
        try:
            recs, ties, method = ranked_records(suffix)
        except FileNotFoundError as e:
            sys.exit(f"{name}: 找不到合并结果：{e.filename}")
        queries = merge.load_queries_from_raw(suffix)
        known, expanded = {}, {}
        for k in keys:
            rank = next((i for i, x in enumerate(recs, 1) if k in identifiers(x)), None)
            known[f"{k[0]}:{k[1]}"] = {"rank": rank, "in_top": bool(rank and rank <= args.top)}
            expanded[k] = {k} | (identifiers(recs[rank - 1]) if rank else set())
        chased = chase_ranks(suffix, expanded)
        for k in keys:
            known[f"{k[0]}:{k[1]}"]["chase"] = chased.get(k, [])
        report[name] = {"method": method, "merged": len(recs), "ties_at_cutoff": ties, "known": known,
                        "top10": topk_stats(recs, 10, queries, args.ignore_phrases),
                        f"top{args.top}": topk_stats(recs, args.top, queries, args.ignore_phrases)}

    cols = list(report)
    print(f"{'':<34}" + "".join(f"{c:>22}" for c in cols))
    print(f"{'ranking method':<34}" + "".join(f"{report[c]['method']:>22}" for c in cols))
    print(f"{'merged works':<34}" + "".join(f"{report[c]['merged']:>22}" for c in cols))
    print(f"{'works tied at the cutoff':<34}" + "".join(f"{str(report[c]['ties_at_cutoff']):>22}" for c in cols))
    for k in (report[cols[0]]["known"] if cols else {}):
        print(f"{'rank of ' + k[:26]:<34}" + "".join(f"{str(report[c]['known'][k]['rank']):>22}" for c in cols))
        print(f"{'  in chase lists':<34}" + "".join(f"{'; '.join(report[c]['known'][k]['chase']) or '-':>22}"
                                                    for c in cols))
    for block in ("top10", f"top{args.top}"):
        for m in ("conform", "noise", "genai", "abstract", "year_median", "before_2015"):
            print(f"{block + ' ' + m:<34}" + "".join(f"{str(report[c][block][m]):>22}" for c in cols))
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nwritten: {merge.rel(args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
