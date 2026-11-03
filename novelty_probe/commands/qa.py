#!/usr/bin/env python3
"""检索质量检查：每个原始结果文件中，有多少条记录的标题 + 摘要满足原检索式。

用 novelty_probe/text.py 的 Porter 词干还原近似两个 API 的匹配方式：短语按词干逐词连续匹配，
截断词按前缀匹配，NOT 组命中（在全文任何位置）即视为不满足。没有摘要的记录只能用标题判断，所以另列"有摘要者"的比例。
比例低说明 API 返回了大量在标题和摘要层面不满足检索式的记录（例如 OpenAlex 的 search= 会匹配全文）。
注意这只是近似：两个 API 的词干还原都更像 KStem（Krovetz），比 Porter 保守（实测 news ≠ new、universe ≠ university），
Porter 会把更多词形视为同一个词，所以本脚本给出的比例略偏高。

用法：novelty-probe qa [--suffix _v2]
"""
import argparse
import sys
from pathlib import Path

from novelty_probe import i18n, report, runtime
from novelty_probe.i18n import t
from novelty_probe.io import load_json_lenient

from novelty_probe.commands import merge
from novelty_probe.commands.search import parse_query
from novelty_probe.text import Doc, query_match


def check_file(path):
    data = load_json_lenient(path)
    include, exclude = parse_query(data["meta"]["query_original"])
    n = with_abs = ok = ok_abs = 0
    for r in data["records"]:
        hit = query_match(include, Doc(r["title"], r["abstract"]), exclude)
        n += 1
        ok += hit
        if r["abstract"]:
            with_abs += 1
            ok_abs += hit
    return {"file": path.name, "records": n, "with_abstract": with_abs, "conform": ok, "conform_with_abstract": ok_abs}


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Check how many retrieved records satisfy the original Boolean query.")
    ap.add_argument("--suffix", default="", help=t("arg.suffix_only"))
    runtime.add_common_args(ap)
    args = ap.parse_args()
    rt = runtime.init(args)
    runtime.bind_root(vars(merge), rt.root, {"RAW_DIR": "results/raw", "OUT_DIR": "results/merged"})
    files = merge.raw_files(args.suffix)
    if not files:
        sys.exit(t("qa.no_files", suffix=args.suffix))
    rows = [check_file(p) for p in files]
    print(f"{'file':<34} {'n':>4} {'abstract':>8} {'conform (all)':>14} {'conform (with abstract)':>24}")
    for r in rows:
        pct = lambda a, b: f"{a}/{b}" + (f" ({100 * a / b:.0f}%)" if b else "")  # noqa: E731
        print(f"{r['file']:<34} {r['records']:>4} {r['with_abstract']:>8} {pct(r['conform'], r['records']):>14} "
              f"{pct(r['conform_with_abstract'], r['with_abstract']):>24}")
    tot = {k: sum(r[k] for r in rows) for k in ("records", "with_abstract", "conform", "conform_with_abstract")}
    print(f"\ntotal: {tot['conform']}/{tot['records']} records conform; among records with an abstract: "
          f"{tot['conform_with_abstract']}/{tot['with_abstract']}  (Porter approximation of the APIs' KStem-like matching)")
    # 本地匹配的偏差（问题 A4）：服务器端做布尔检索的来源，返回的记录按定义满足检索式
    for src, v in report.local_match(files).items():
        if v["with_abstract"]:
            print(t("qa.local_bias", source=src, k=v["with_abstract"] - v["conforming"], n=v["with_abstract"],
                    p=round(100 * v["nonconforming_share"], 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
