#!/usr/bin/env python3
"""运行一条命令，并把命令与输出追加到 logs/RUN_LOG.md（PROJECT.md 规则 c）。

用法：python3 scripts/logrun.py "<步骤名>" -- <命令> [参数 ...]
例如：python3 scripts/logrun.py "T3 检索" -- python3 scripts/search.py

命令在项目根目录下运行；输出照常实时打印到终端；退出码与被运行的命令相同。
"""
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "RUN_LOG.md"


def main():
    args = sys.argv[1:]
    if "--" not in args or args.index("--") == 0 or args.index("--") == len(args) - 1:
        sys.exit('用法：python3 scripts/logrun.py "<步骤名>" -- <命令> [参数 ...]')
    sep = args.index("--")
    title, cmd = " ".join(args[:sep]), args[sep + 1:]
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}  # 子进程实时输出、统一编码
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.exit(f"找不到命令：{cmd[0]}")
    lines = []
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append(line)
    code = proc.wait()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", newline="\n") as f:  # logrun 不依赖 novelty_probe，可单独复制使用；换行固定为 \n
        f.write(f"\n---\n\n## [{started}] {title}\n\n**命令**\n\n```bash\n{command_line(cmd)}\n```\n\n"
                f"**输出**（退出码 {code}）\n\n```\n{''.join(lines).rstrip()}\n```\n")
    return code


def command_line(cmd):
    """日志里的命令：POSIX 系统按 shell 引用规则，Windows 按 cmd 规则；两者都附上原始参数列表（JSON），便于在另一系统上复现。"""
    quoted = subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd)
    return quoted + "\n# argv: " + json.dumps(cmd, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
