"""测试启动的子进程在启动时装上网络护栏（CHILD_ENV 的 PYTHONPATH 指向本目录）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import netguard  # noqa: E402

netguard.install()
