#!/usr/bin/env python3
"""一条命令跑完脚本步骤：novelty-probe run [--suffix _v2] [--queries 文件] [--from 步骤] [--to 步骤] [--dry-run]

步骤（每一步都在子进程里运行，命令与输出写进 logs/RUN_LOG.md，Step 编号自动接着日志里的最后一个）：
  check    检查检索式（search --dry-run，不联网）
  search   检索（T3）
  qa       检索质量检查（满足检索式的比例、本地匹配的偏差）
  merge    合并去重；写出候选表、RIS、运行清单与检索报告（T4）
  authors  补查作者：只在候选表里有缺作者、带 DOI 的候选时运行（阶段 4 之后检索的结果一般不需要）
  enrich   从同一研究的其他版本补摘要与 arXiv ID（为 T5 证据表做准备）
出错即停，并给出从出错的一步续跑的命令（--from）。T5 的证据表由 AI 助手写，见 HOWTO.md。
检索式文件默认为 queries/queries{后缀}.json；--http-mode、--cassette、--cache-dir、--refresh 传给联网的步骤。
"""
import argparse
import csv
import os
import shlex
import sys
from pathlib import Path

from novelty_probe import i18n, runtime
from novelty_probe.commands.logrun import run_logged
from novelty_probe.i18n import tr

STEPS = ("check", "search", "qa", "merge", "authors", "enrich")
TITLES = {
    "check": ("T3 检查检索式", "T3 check the queries"),
    "search": ("T3 检索", "T3 search"),
    "qa": ("T3 质量检查", "T3 quality check"),
    "merge": ("T4 合并去重", "T4 merge and deduplicate"),
    "authors": ("T5 补查作者", "T5 missing authors"),
    "enrich": ("T5 补摘要", "T5 abstracts from other versions"),
}
NETWORK = ("search", "authors", "enrich")


def http_args(args):
    out = []
    if args.http_mode:
        out += ["--http-mode", args.http_mode]
    if args.cassette:
        out += ["--cassette", str(Path(args.cassette).resolve())]
    if args.cache_dir:
        out += ["--cache-dir", str(Path(args.cache_dir).resolve())]
    if args.refresh:
        out.append("--refresh")
    return out


def step_argv(step, args, queries, top_k):
    """一步要运行的 novelty-probe 命令（路径相对于项目目录：子进程在项目目录里运行）。"""
    s = args.suffix
    sfx = ["--suffix", s] if s else []
    common = (["--config", str(Path(args.config).resolve())] if args.config else []) + (["--lang", args.lang] if args.lang else [])
    net = http_args(args) if step in NETWORK else []
    cand = f"results/merged/candidates{s}.csv"
    if step == "check":
        return ["search", "--dry-run", "--queries", queries, *common]
    if step == "search":
        return ["search", "--queries", queries, *sfx, *common, *net]
    if step in ("qa", "merge"):
        return [step, *sfx, *common]
    if step == "authors":
        return ["authors", "--top", str(top_k), "--candidates", cand, "--out", f"evidence/authors{s}.json", *common, *net]
    top = ["--top", str(args.enrich_top)] if args.enrich_top else []
    return ["enrich", *top, "--candidates", cand, "--out", f"evidence/enrichment{s}.json", *common, *net]


def missing_authors(cand_file, top_k):
    """候选表前 top_k 篇里缺作者、带 DOI 的条数；没有 authors 列（--legacy 或阶段 4 之前的格式）时按全部缺作者计。"""
    with cand_file.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))[:top_k]
    if rows and "authors" not in rows[0]:
        return sum(1 for r in rows if r.get("doi"))
    return sum(1 for r in rows if not (r.get("authors") or "").strip() and r.get("doi"))


def resume_command(step):
    """续跑命令：原来的参数去掉 --from，再从 step 开始。"""
    args, out, i = sys.argv[1:], [], 0
    while i < len(args):
        if args[i] == "--from":
            i += 2
            continue
        if args[i].startswith("--from="):
            i += 1
            continue
        out.append(args[i])
        i += 1
    return shlex.join(["novelty-probe", "run", *out, "--from", step])


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Run the scripted steps: check the queries, search, quality check, merge, "
                                             "missing authors, abstracts from other versions. Every step goes to the run log.")
    ap.add_argument("--suffix", default="", help=i18n.t("arg.suffix_out"))
    ap.add_argument("--queries", default=None,
                    help=tr("检索式文件（默认 queries/queries{后缀}.json）", "Query file (default: queries/queries{suffix}.json)"))
    ap.add_argument("--from", dest="start", choices=STEPS, default=STEPS[0], help=tr("从这一步开始", "Start at this step"))
    ap.add_argument("--to", dest="stop", choices=STEPS, default=STEPS[-1], help=tr("到这一步为止", "Stop after this step"))
    ap.add_argument("--enrich-top", type=int, default=None,
                    help=tr("补摘要处理前多少篇（默认取配置 enrich.top）", "Candidates for the abstract step (default: config enrich.top)"))
    ap.add_argument("--dry-run", action="store_true", help=tr("只打印各步的命令，不运行", "Only print the commands of each step"))
    runtime.add_common_args(ap, network=True)
    args = ap.parse_args()
    rt = runtime.init(args, network=False)
    root, cfg = rt.root, rt.cfg
    os.environ["NP_LANG"] = rt.lang            # 子进程与运行日志用同一种语言
    first, last = STEPS.index(args.start), STEPS.index(args.stop)
    if first > last:
        ap.error(tr("--from 在 --to 之后", "--from comes after --to"))
    steps = STEPS[first:last + 1]
    queries = args.queries or f"queries/queries{args.suffix}.json"
    q = Path(queries)
    if not q.is_absolute() and not (root / q).is_file() and q.is_file():
        queries = str(q.resolve())             # 相对于当前目录给出的文件：各步骤在项目目录里运行，改用绝对路径
    if ("check" in steps or "search" in steps) and not (root / queries).is_file():
        print(tr("找不到检索式文件 {f}：先按 HOWTO.md 第 3 节写好检索式，或用 --queries 指定文件。",
                 "Query file {f} not found: write the queries first (HOWTO.md section 3), or name the file with --queries.",
                 f=queries), file=sys.stderr)
        return 2
    top_k = cfg["merge"]["top_k"]

    if args.dry_run:
        print(tr("项目目录：{d}", "project folder: {d}", d=root))
        for step in steps:
            note = tr("（只在有缺作者的候选时运行）", " (only if some candidates lack authors)") if step == "authors" else ""
            print(f"{step:<8} {shlex.join(['novelty-probe', *step_argv(step, args, queries, top_k)])}{note}")
        return 0

    done = []
    for step in steps:
        if step == "authors":
            cand = root / "results" / "merged" / f"candidates{args.suffix}.csv"
            n = missing_authors(cand, top_k) if cand.is_file() else top_k
            if not n:
                print(tr("\n[authors] 跳过：候选都已带作者（检索时取得）", "\n[authors] skipped: every candidate already has authors "
                                                                     "(from the search)"))
                continue
        argv = step_argv(step, args, queries, top_k)
        print(f"\n[{step}] " + shlex.join(["novelty-probe", *argv]))
        title = tr(*TITLES[step]) + (f" {args.suffix.lstrip('_')}" if args.suffix else "")
        code, logged = run_logged(title, [sys.executable, "-m", "novelty_probe", *argv], root,
                                  display=["novelty-probe", *argv])
        done.append((step, logged, code))
        if code != 0:
            print()
            print(tr("在 {s} 这一步停下（退出码 {c}；已写进运行日志：{t}）。按上面的输出排除问题后，从这一步续跑：",
                     "Stopped at step {s} (exit code {c}; logged as: {t}). Fix the cause shown above, then resume with:",
                     s=step, c=code, t=logged), file=sys.stderr)
            print(f"  {resume_command(step)}", file=sys.stderr)
            if step == "search":
                print(tr("部分请求失败时，也可以先用 novelty-probe search --ids <检索式> --sources <来源> 补跑，再从 qa 续跑。",
                         "If only some requests failed, you can instead re-run them with novelty-probe search --ids <queries> "
                         "--sources <sources>, then resume from qa."), file=sys.stderr)
            return code

    print()
    print(tr("完成 {n} 步，均已写进 logs/RUN_LOG.md：", "Done: {n} step(s), all in logs/RUN_LOG.md:", n=len(done)))
    for step, logged, _ in done:
        print(f"  {logged}")
    if "merge" in steps:
        s = args.suffix
        print(tr("候选与报告：results/merged/candidates{s}.csv、candidates{s}.ris、search_report{s}.md",
                 "candidates and report: results/merged/candidates{s}.csv, candidates{s}.ris, search_report{s}.md", s=s))
    if steps[-1] == "enrich":
        print(tr("下一步（T5）：让 AI 助手按 HOWTO.md 第 6 节写证据表。",
                 "Next (T5): have the AI assistant write the evidence table (HOWTO.md section 6)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
