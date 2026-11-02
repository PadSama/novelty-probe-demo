#!/usr/bin/env python3
"""检索质量检查：每个原始结果文件中，有多少条记录的标题 + 摘要满足原检索式。

用 scripts/textmatch.py 的 Porter 词干还原近似两个 API 的匹配方式：短语按词干逐词连续匹配，
截断词按前缀匹配，NOT 组命中即视为不满足。没有摘要的记录只能用标题判断，所以另列"有摘要者"的比例。
比例低说明 API 返回了大量在标题和摘要层面不满足检索式的记录（例如 OpenAlex 的 search= 会匹配全文）。

用法：python3 scripts/qa.py [--suffix _v2]
"""
import argparse
import json
import sys

import merge
from search import parse_query
from textmatch import Doc, query_match


def check_file(path):
    data = json.loads(path.read_text(encoding="utf-8"))
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
    ap = argparse.ArgumentParser(description="Check how many retrieved records satisfy the original Boolean query.")
    ap.add_argument("--suffix", default="", help="只检查这个后缀的结果文件，如 _v2（默认无后缀，即 v1）")
    args = ap.parse_args()
    files = merge.raw_files(args.suffix)
    if not files:
        sys.exit(f"results/raw/ 中没有后缀为 '{args.suffix}' 的结果文件")
    rows = [check_file(p) for p in files]
    print(f"{'file':<34} {'n':>4} {'abstract':>8} {'conform (all)':>14} {'conform (with abstract)':>24}")
    for r in rows:
        pct = lambda a, b: f"{a}/{b}" + (f" ({100 * a / b:.0f}%)" if b else "")  # noqa: E731
        print(f"{r['file']:<34} {r['records']:>4} {r['with_abstract']:>8} {pct(r['conform'], r['records']):>14} "
              f"{pct(r['conform_with_abstract'], r['with_abstract']):>24}")
    tot = {k: sum(r[k] for r in rows) for k in ("records", "with_abstract", "conform", "conform_with_abstract")}
    print(f"\ntotal: {tot['conform']}/{tot['records']} records conform; among records with an abstract: "
          f"{tot['conform_with_abstract']}/{tot['with_abstract']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
