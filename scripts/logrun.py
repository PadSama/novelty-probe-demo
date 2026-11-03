#!/usr/bin/env python3
"""运行一条命令，并把命令与输出追加到 logs/RUN_LOG.md（PROJECT.md 规则 c）。

用法：python3 scripts/logrun.py [--root 目录] "<步骤名>" -- <命令> [参数 ...]
例如：python3 scripts/logrun.py "T3 检索" -- python3 scripts/search.py

项目根目录：--root > 环境变量 NOVELTY_PROBE_ROOT > 从当前目录向上找 novelty-probe.json 或 PROJECT.md > 本脚本所在的仓库
（与 novelty_probe/paths.py 的 find_root 相同）。日志写到该目录的 logs/RUN_LOG.md；命令在该目录下运行，并通过
NOVELTY_PROBE_ROOT 告诉子进程同一个根目录。输出照常实时打印到终端；退出码与被运行的命令相同。
本脚本不依赖 novelty_probe 包，可以单独复制使用。
"""
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKERS = ("novelty-probe.json", "PROJECT.md")
USAGE = {"zh": '用法：python3 scripts/logrun.py [--root 目录] "<步骤名>" -- <命令> [参数 ...]',
         "en": 'usage: python3 scripts/logrun.py [--root DIR] "<step name>" -- <command> [args ...]'}


def lang():
    return "en" if os.environ.get("NP_LANG") == "en" else "zh"


def find_root(explicit=None, env=None, start=None):
    env = os.environ if env is None else env
    if explicit:
        return Path(explicit).resolve()
    if env.get("NOVELTY_PROBE_ROOT"):
        return Path(env["NOVELTY_PROBE_ROOT"]).resolve()
    here = Path(start or os.getcwd()).resolve()
    for d in (here, *here.parents):
        if any((d / m).is_file() for m in MARKERS):
            return d
    return ROOT


def main():
    args = sys.argv[1:]
    explicit = None
    if args[:1] == ["--root"] and len(args) > 1:
        explicit, args = args[1], args[2:]
    elif args[:1] and args[0].startswith("--root="):
        explicit, args = args[0].split("=", 1)[1], args[1:]
    if "--" not in args or args.index("--") == 0 or args.index("--") == len(args) - 1:
        sys.exit(USAGE[lang()])
    root = find_root(explicit)
    log = root / "logs" / "RUN_LOG.md"
    sep = args.index("--")
    title, cmd = " ".join(args[:sep]), args[sep + 1:]
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8",  # 子进程实时输出、统一编码
           "NOVELTY_PROBE_ROOT": str(root)}                                      # 子进程用同一个项目根目录
    try:
        proc = subprocess.Popen(cmd, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.exit(("command not found: {c}" if lang() == "en" else "找不到命令：{c}").format(c=cmd[0]))
    lines = []
    for line in proc.stdout:
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
        f.write(f"\n---\n\n## [{started}] {title}\n\n{head}\n\n```bash\n{command_line(cmd)}\n```\n\n"
                f"{out}\n\n```\n{''.join(lines).rstrip()}\n```\n")
    return code


def command_line(cmd):
    """日志里的命令：POSIX 系统按 shell 引用规则，Windows 按 cmd 规则；两者都附上原始参数列表（JSON），便于在另一系统上复现。"""
    quoted = subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd)
    return quoted + "\n# argv: " + json.dumps(cmd, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
