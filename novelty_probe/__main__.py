"""python -m novelty_probe <命令> …（与安装后的 novelty-probe 命令相同）。"""
import sys

from novelty_probe.cli import main

sys.exit(main())
