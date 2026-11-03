"""命令行入口：novelty-probe <命令> [参数] [--log "<步骤名>"]（也可以 python -m novelty_probe <命令> …）。

各命令的代码在 novelty_probe/commands/<命令>.py；scripts/<命令>.py 是旧的入口，转发到这里，旧命令照常可用。
--log "<步骤名>"：在子进程里运行这条命令，并把命令与输出写进项目的 logs/RUN_LOG.md（自动接着编 Step 号），
与 novelty-probe logrun "<步骤名>" -- novelty-probe <命令> … 相同。
"""
import importlib
import sys

from . import __version__, i18n
from .i18n import tr
from .io import configure_console
from .paths import ProjectNotFound, find_root

# 命令 → (中文说明, 英文说明)；顺序即帮助里的顺序（大致是流程顺序）
COMMANDS = {
    "init": ("新建项目目录（规则、助手说明、操作指南、想法模板、配置、运行日志）",
             "Create a project folder (rules, assistant instructions, guide, idea template, config, run log)"),
    "run": ("一条命令跑完脚本步骤：检查检索式 → 检索 → 质量检查 → 合并 → 补查作者 → 补摘要",
            "Run the scripted steps: check queries → search → quality check → merge → missing authors → abstracts"),
    "search": ("T3 检索（--dry-run 只检查检索式，不联网）", "T3 search (--dry-run only checks the queries, offline)"),
    "qa": ("检索质量检查：满足检索式的比例、本地匹配的偏差", "Search quality: share of records satisfying the query, local matching bias"),
    "merge": ("T4 合并去重；写出候选表、RIS、运行清单与检索报告", "T4 merge and deduplicate; write candidates, RIS, run manifest and search report"),
    "authors": ("补查候选缺的作者（OpenAlex）", "Look up missing authors of candidates (OpenAlex)"),
    "enrich": ("从同一研究的其他版本补摘要与 arXiv ID", "Abstracts and arXiv IDs from other versions of the same work"),
    "evidence": ("证据表：check 检查、import-md 转 JSON、render 生成 Markdown", "Evidence table: check, import-md, render"),
    "verify": ("核验证据表里的 DOI", "Verify the DOIs in the evidence table"),
    "snowball": ("引文追踪（一步，或两步共被引）", "Citation chasing (one hop or two-hop co-citation)"),
    "compare": ("比较几轮结果与已知文献的名次", "Compare rounds and the ranks of known papers"),
    "export": ("导出 RIS：候选、全部合并记录或证据表各行", "Export RIS: candidates, all merged works or evidence-table rows"),
    "report": ("检索报告：按运行清单重新生成、比较两次运行", "Search report: render from a run manifest, diff two runs"),
    "config": ("查看与检查配置 novelty-probe.json", "Show and check the configuration (novelty-probe.json)"),
    "logrun": ("运行任意命令，并把命令与输出写进运行日志", "Run any command and append it with its output to the run log"),
}


def usage():
    lines = [tr("novelty-probe {v}：围绕研究想法查找文献证据（只找证据，不判断新颖性）",
                "novelty-probe {v}: collect literature evidence around a research idea (evidence only, no novelty verdicts)",
                v=__version__),
             "",
             tr("用法：novelty-probe <命令> [参数 ...] [--log \"<步骤名>\"]",
                "usage: novelty-probe <command> [args ...] [--log \"<step name>\"]"),
             "",
             tr("命令：", "commands:")]
    width = max(map(len, COMMANDS))
    lines += [f"  {name:<{width}}  {tr(*desc)}" for name, desc in COMMANDS.items()]
    lines += ["",
              tr("各命令的参数：novelty-probe <命令> --help。--log \"<步骤名>\" 把这条命令与输出写进 logs/RUN_LOG.md。",
                 "Options of a command: novelty-probe <command> --help. --log \"<step name>\" appends the command and its "
                 "output to logs/RUN_LOG.md."),
              tr("操作指南见项目目录里的 HOWTO.md；版本：novelty-probe --version。",
                 "See HOWTO.md in the project folder; version: novelty-probe --version.")]
    return "\n".join(lines)


def pop_log(args):
    """从参数里取出 --log <步骤名> / --log=<步骤名>；返回 (步骤名或 None, 其余参数)。"""
    out, title, i = [], None, 0
    while i < len(args):
        a = args[i]
        if a == "--log" and i + 1 < len(args):
            title, i = args[i + 1], i + 2
            continue
        if a.startswith("--log="):
            title, i = a.split("=", 1)[1], i + 1
            continue
        out.append(a)
        i += 1
    return title, out


def root_option(args):
    for i, a in enumerate(args):
        if a == "--root" and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--root="):
            return a.split("=", 1)[1]
    return None


def run_command(name, args):
    """在本进程里运行一个命令（argparse 看到的程序名为 novelty-probe <命令>）。"""
    module = importlib.import_module(f"novelty_probe.commands.{name}")
    saved = sys.argv
    sys.argv = [f"novelty-probe {name}", *args]
    try:
        code = module.main()
    finally:
        sys.argv = saved
    return code if isinstance(code, int) else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    i18n.prepare(argv)
    configure_console()
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage())
        return 0
    if argv[0] in ("-V", "--version", "version"):
        print(f"novelty-probe {__version__}")
        return 0
    name, rest = argv[0], argv[1:]
    if name not in COMMANDS:
        print(tr("未知命令：{c}", "unknown command: {c}", c=name), file=sys.stderr)
        print(usage(), file=sys.stderr)
        return 2
    title, rest = pop_log(rest)
    if title is None:
        return run_command(name, rest)
    if name in ("logrun", "run"):
        print(tr("{c} 自己会写运行日志，不用加 --log", "{c} writes the run log itself; --log is not needed", c=name),
              file=sys.stderr)
        return 2
    try:
        root = find_root(root_option(rest))
    except ProjectNotFound as e:
        print(e, file=sys.stderr)
        return 2
    from .commands.logrun import run_logged
    code, _ = run_logged(title, [sys.executable, "-m", "novelty_probe", name, *rest], root,
                         display=["novelty-probe", name, *rest])
    return code


if __name__ == "__main__":
    sys.exit(main())
