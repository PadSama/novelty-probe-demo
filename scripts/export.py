#!/usr/bin/env python3
"""导出 RIS（Zotero、EndNote 等文献管理软件的通用导入格式；novelty_probe/export.py）。

合并时已经自动写出候选的 RIS（results/merged/candidates{后缀}.ris），一般不用再运行本脚本。需要别的范围时：
  python3 scripts/export.py --suffix _v1b --all                       # 全部合并记录 → results/merged/merged_v1b.ris
  python3 scripts/export.py --evidence evidence/evidence_table.md      # 证据表各行（附各面的标注）→ evidence/evidence_table.ris
  python3 scripts/export.py --suffix _v1b                              # 候选（按候选表的顺序），与合并时写出的相同
证据表的行按 DOI / arXiv ID 对应到合并结果（默认按文件名后缀推断，如 evidence_table_v2 → merged_v2.json），取其完整的作者、
出处与摘要；对应不上的只用证据表里的题目、作者、年份与标识符。值都取自检索结果，不补写。不联网。
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe import evidence, export, i18n, rank, runtime
from novelty_probe.i18n import tr
from novelty_probe.io import load_json_lenient
from novelty_probe.paths import rel


def evidence_entries(doc, index):
    """证据表各行 → (记录, 关键词, 说明)。"""
    facets = doc["meta"].get("facets") or []
    lang = i18n.get_language()
    recs, kws, notes = [], [], []
    for row in doc["rows"]:
        ids = evidence.identifiers(row.get("doi"), row.get("arxiv_id"))
        x = index.record_for(ids) if (index and ids) else None
        note = f"novelty-probe evidence table, rank {row.get('rank')}"
        if x is None:
            listed = row.get("authors") or ""
            names = [n.strip() for n in listed.replace(" et al.", "").split(";") if n.strip()]
            x = {"title": row.get("title"), "authors": names, "year": row.get("year"), "doi": row.get("doi"),
                 "arxiv_id": row.get("arxiv_id")}
            if "et al." in listed:
                note += "; authors as listed in the evidence table (et al.)"
        labels = row.get("labels") or {}
        kw = []
        for f in facets:
            if f["key"] in labels:
                kw.append(f"{f['label'].get(lang) or next(iter(f['label'].values()))}: {labels[f['key']]}")
        recs.append(x)
        kws.append(kw)
        notes.append(note)
    return recs, kws, notes


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Export RIS: candidates (default), all merged records, or evidence-table rows.")
    ap.add_argument("--suffix", default="", help=tr("合并结果的后缀，如 _v2", "Suffix of the merged results, e.g. _v2"))
    ap.add_argument("--all", action="store_true", help=tr("导出全部合并记录", "Export all merged records"))
    ap.add_argument("--evidence", type=Path, help=tr("导出这张证据表的各行（.md 或 .json）", "Export the rows of this evidence table (.md or .json)"))
    ap.add_argument("--results", type=Path, help=tr("证据表对应的合并结果（默认按后缀推断）", "Merged results for the evidence table (default: inferred from its suffix)"))
    ap.add_argument("--out", type=Path, help=tr("输出路径", "Output path"))
    runtime.add_common_args(ap)
    args = ap.parse_args()
    rt = runtime.init(args)
    root = rt.root
    merged_dir = root / "results" / "merged"
    if args.evidence:
        doc = evidence.load(args.evidence, rt.cfg)
        stem = args.evidence.stem
        suffix = stem[len("evidence_table"):] if stem.startswith("evidence_table") else ""
        results = args.results or merged_dir / f"merged{suffix}.json"
        index = evidence.load_index(results) if results.is_file() else None
        recs, kws, notes = evidence_entries(doc, index)
        out = args.out or args.evidence.with_suffix(".ris")
        export.write_ris(out, recs, kws, notes)
    else:
        merged_file = merged_dir / f"merged{args.suffix}.json"
        data = load_json_lenient(merged_file)
        recs = sorted(data["records"], key=rank.sort_key) if "method" in data["meta"] else data["records"]
        cand_file = merged_dir / f"candidates{args.suffix}.csv"
        if not args.all and cand_file.is_file():          # 候选按候选表的顺序（--legacy 的结果排序方法不同）
            with cand_file.open(encoding="utf-8-sig", newline="") as f:
                order = [r["merged_id"] for r in csv.DictReader(f)]
            by_id = {x["merged_id"]: x for x in data["records"]}
            recs = [by_id[m] for m in order if m in by_id]
        elif not args.all:
            recs = recs[:(data["meta"].get("candidates") or {}).get("top_k") or len(recs)]
        out = args.out or merged_dir / (f"merged{args.suffix}.ris" if args.all else f"candidates{args.suffix}.ris")
        export.write_ris(out, recs)
    print(tr("已写入：{f}（{n} 条）", "written: {f} ({n} records)", f=rel(out, root), n=len(recs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
