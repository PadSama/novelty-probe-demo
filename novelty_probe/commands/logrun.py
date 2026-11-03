#!/usr/bin/env python3
"""运行一条命令，并把命令与输出追加到 logs/RUN_LOG.md（PROJECT.md 规则 3）。

用法：novelty-probe logrun [--root 目录] "<步骤名>" -- <命令> [参数 ...]
例如：novelty-probe logrun "T3 检索" -- novelty-probe search
更简单的写法：任一命令后加 --log "<步骤名>"，如 novelty-probe search --log "T3 检索"（novelty_probe/cli.py）。

项目根目录：--root > 环境变量 NOVELTY_PROBE_ROOT > 从当前目录向上找 novelty-probe.json 或 PROJECT.md（novelty_probe/paths.py）。
日志写到该目录的 logs/RUN_LOG.md；命令在该目录下运行，并通过 NOVELTY_PROBE_ROOT 告诉子进程同一个根目录。
输出照常实时打印到终端；退出码与被运行的命令相同。
标题不以 "Step <编号>" 开头时，自动接着日志里最大的 Step 编号加上 "Step N — "（与手写条目的格式一致）。
写进日志的命令与输出里，用户目录（其中常含用户名）记成 ~；终端上照常显示原样。
"""
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from novelty_probe.paths import ProjectNotFound, find_root

USAGE = {"zh": '用法：novelty-probe logrun [--root 目录] "<步骤名>" -- <命令> [参数 ...]',
         "en": 'usage: novelty-probe logrun [--root DIR] "<step name>" -- <command> [args ...]'}
STEP_RE = re.compile(r"^## \[[^\]]*\] Step (\d+)\b", re.M)
TITLE_STEP_RE = re.compile(r"^Step \d+\b")
PACKAGE_PARENT = str(Path(__file__).resolve().parent.parent.parent)   # 含 novelty_probe 的目录：子进程里 python -m novelty_probe 可用


def lang():
    return "en" if os.environ.get("NP_LANG") == "en" else "zh"


def next_step(log):
    """日志里最大的 Step 编号加 1；没有日志或没有编号时为 1（Step 0 留给新建项目）。"""
    try:
        text = Path(log).read_text(encoding="utf-8")
    except OSError:
        return 1
    nums = [int(n) for n in STEP_RE.findall(text)]
    return max(nums) + 1 if nums else 1


def numbered(title, log):
    return title if TITLE_STEP_RE.match(title) else f"Step {next_step(log)} — {title}"


def mask_home(text):
    """日志可能随论文公开：把用户目录（如 /Users/alice、C:\\Users\\alice）换成 ~。
    只替换完整的目录名（/home/alice2 不算），Windows 上不分大小写。"""
    home = Path.home()
    flags = re.IGNORECASE if os.name == "nt" else 0
    for h in sorted({str(home), home.as_posix()}, key=len, reverse=True):
        if len(h) > 1:
            text = re.sub(re.escape(h) + r"(?![A-Za-z0-9_.-])", "~", text, flags=flags)
    return text


def command_line(cmd):
    """日志里的命令：POSIX 系统按 shell 引用规则，Windows 按 cmd 规则；两者都附上原始参数列表（JSON），便于在另一系统上复现。"""
    quoted = subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd)
    return quoted + "\n# argv: " + json.dumps(cmd, ensure_ascii=False)


def run_logged(title, cmd, root, display=None, echo=True):
    """在 root 下运行 cmd，输出实时打印，并把命令与输出追加到 root/logs/RUN_LOG.md。返回 (退出码, 日志标题)。
    display：写进日志的命令（默认同 cmd）；novelty-probe 自己调用时记成 novelty-probe …，不写本机的解释器路径。"""
    root = Path(root).resolve()
    log = root / "logs" / "RUN_LOG.md"
    title = numbered(title, log)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pythonpath = os.pathsep.join(filter(None, [PACKAGE_PARENT, os.environ.get("PYTHONPATH")]))
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8",  # 子进程实时输出、统一编码
           "NOVELTY_PROBE_ROOT": str(root), "PYTHONPATH": pythonpath}           # 子进程用同一个项目根目录与同一个包
    try:
        proc = subprocess.Popen(cmd, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.exit(("command not found: {c}" if lang() == "en" else "找不到命令：{c}").format(c=cmd[0]))
    lines = []
    for line in proc.stdout:
        if echo:
            sys.stdout.write(line)
            sys.stdout.flush()
        lines.append(line)
    code = proc.wait()
    log.parent.mkdir(parents=True, exist_ok=True)
    if lang() == "en":
        head, out = "**Command**", f"**Output** (exit code {code})"
    else:
        head, out = "**命令**", f"**输出**（退出码 {code}）"
    with log.open("a", encoding="utf-8", newline="\n") as f:  # 换行固定为 \n
        f.write(f"\n---\n\n## [{started}] {title}\n\n{head}\n\n```bash\n{mask_home(command_line(display or cmd))}\n```\n\n"
                f"{out}\n\n```\n{mask_home(''.join(lines).rstrip())}\n```\n")
    return code, title


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    from novelty_probe import i18n
    i18n.set_language(lang())
    explicit = None
    if args[:1] == ["--root"] and len(args) > 1:
        explicit, args = args[1], args[2:]
    elif args[:1] and args[0].startswith("--root="):
        explicit, args = args[0].split("=", 1)[1], args[1:]
    if "--" not in args or args.index("--") == 0 or args.index("--") == len(args) - 1:
        sys.exit(USAGE[lang()])
    try:
        root = find_root(explicit)
    except ProjectNotFound as e:
        sys.exit(str(e))
    sep = args.index("--")
    code, _ = run_logged(" ".join(args[:sep]), args[sep + 1:], root)
    return code


if __name__ == "__main__":
    sys.exit(main())
