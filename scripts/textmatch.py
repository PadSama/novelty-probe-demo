#!/usr/bin/env python3
"""兼容层：文本匹配已移入 novelty_probe/text.py（阶段 3）。旧的 `from textmatch import …` 照常可用，
得到的是同一组对象（不会因为两种导入方式而各有一份状态）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe.text import *  # noqa: E402,F401,F403
