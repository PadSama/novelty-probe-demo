#!/usr/bin/env python3
"""运行清单与检索报告（novelty_probe/report.py）。合并时已经自动写出，一般不用运行本脚本。

  novelty-probe report render results/merged/run_manifest_v1b.json --lang en   # 按清单重新生成检索报告（如换成英文）
  novelty-probe report diff OLD.json NEW.json                                   # 比较两份运行清单：检索结果与候选的变化
不联网。
"""
import argparse
import json
import sys
from pathlib import Path

from novelty_probe import i18n, report, runtime
from novelty_probe.i18n import tr
from novelty_probe.io import load_json_lenient, write_text
from novelty_probe.paths import rel


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Render a search report from a run manifest, or compare two manifests.")
    ap.add_argument("action", choices=("render", "diff"))
    ap.add_argument("manifests", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, help=tr("render 的输出路径（默认打印）", "Output path for render (default: print)"))
    runtime.add_common_args(ap)
    args = ap.parse_args()
    rt = runtime.init(args)
    if args.action == "render":
        m = load_json_lenient(args.manifests[0])
        stem = args.manifests[0].stem
        text = report.render_report(m, stem[len("run_manifest"):] if stem.startswith("run_manifest") else "")
        if args.out:
            write_text(args.out, text)
            print(tr("已写入：{f}", "written: {f}", f=rel(args.out, rt.root)))
        else:
            print(text, end="")
        return 0
    if len(args.manifests) != 2:
        ap.error(tr("diff 需要两份清单", "diff needs two manifests"))
    d = report.diff(*(load_json_lenient(p) for p in args.manifests))
    s, c = d["searches"], d["candidates"]
    print(tr("检索结果：新增 {a}，去掉 {r}，变化 {c}", "search results: {a} added, {r} removed, {c} changed",
             a=len(s["added"]), r=len(s["removed"]), c=len(s["changed"])))
    for ch in s["changed"]:
        print(f"  {ch['file']}: total_hits {ch['total_hits'][0]} → {ch['total_hits'][1]}, saved {ch['returned'][0]} → {ch['returned'][1]}")
    print(tr("候选：保留 {k}，新进 {a}，移出 {r}", "candidates: {k} kept, {a} new, {r} dropped", k=c["kept"], a=len(c["added"]), r=len(c["removed"])))
    for x in c["added"]:
        print(f"  + {x.get('doi') or x.get('arxiv_id') or ''} {x.get('title') or ''}")
    for x in c["removed"]:
        print(f"  - {x.get('doi') or x.get('arxiv_id') or ''} {x.get('title') or ''}")
    print(tr("配置相同" if d["config"]["same"] else "配置不同", "same configuration" if d["config"]["same"] else "different configuration"))
    print(json.dumps({"summary": {"changed_searches": len(s["changed"]), "new_candidates": len(c["added"]),
                                  "dropped_candidates": len(c["removed"])}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
