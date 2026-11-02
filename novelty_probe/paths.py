"""项目根目录与路径显示。

find_root()：命令行 --root > 环境变量 NOVELTY_PROBE_ROOT > 从当前目录向上找 novelty-probe.json 或 PROJECT.md > 包所在仓库。
rel()：项目内的路径显示为相对路径（POSIX 分隔符，日志在各系统上一致），项目外的显示为绝对路径。
"""
import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
MARKERS = ("novelty-probe.json", "PROJECT.md")


def find_root(explicit=None, env=os.environ, start=None):
    if explicit:
        return Path(explicit).resolve()
    if env.get("NOVELTY_PROBE_ROOT"):
        return Path(env["NOVELTY_PROBE_ROOT"]).resolve()
    here = Path(start or os.getcwd()).resolve()
    for d in (here, *here.parents):
        if any((d / m).is_file() for m in MARKERS):
            return d
    return PACKAGE_ROOT


def rel(path, root=None):
    """项目内 → 相对路径（正斜杠）；项目外 → 绝对路径。"""
    p = Path(path).resolve()
    root = Path(root or PACKAGE_ROOT).resolve()
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)
