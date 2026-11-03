#!/usr/bin/env python3
"""旧的命令入口，转发到 novelty-probe export（代码在 novelty_probe/commands/export.py）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # 未安装时也能找到 novelty_probe 包
from novelty_probe.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["export", *sys.argv[1:]]))
