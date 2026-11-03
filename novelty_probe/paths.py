"""项目根目录与路径显示。

find_root()：命令行 --root > 环境变量 NOVELTY_PROBE_ROOT > 从当前目录向上找 novelty-probe.json 或 PROJECT.md
> 源码仓库（只在包位于一个项目目录里时，即从源码仓库运行；安装后的包不会把结果写进安装位置）。
rel()：项目内的路径显示为相对路径（POSIX 分隔符，日志在各系统上一致），项目外的显示为绝对路径。
"""
import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent   # 源码仓库；安装后是 site-packages 一类的目录
MARKERS = ("novelty-probe.json", "PROJECT.md")


class ProjectNotFound(Exception):
    """找不到项目目录（没有 --root，当前目录及其上级都没有 novelty-probe.json 或 PROJECT.md）。"""


def find_root(explicit=None, env=os.environ, start=None):
    if explicit:
        return Path(explicit).resolve()
    if env.get("NOVELTY_PROBE_ROOT"):
        return Path(env["NOVELTY_PROBE_ROOT"]).resolve()
    here = Path(start or os.getcwd()).resolve()
    for d in (here, *here.parents):
        if any((d / m).is_file() for m in MARKERS):
            return d
    if any((PACKAGE_ROOT / m).is_file() for m in MARKERS):
        return PACKAGE_ROOT
    from .i18n import tr
    raise ProjectNotFound(tr("找不到项目目录：{d} 及其上级目录里都没有 novelty-probe.json 或 PROJECT.md。"
                             "先用 novelty-probe init <目录> 新建项目并进入该目录，或用 --root 指定项目目录。",
                             "No project folder found: neither {d} nor any parent has novelty-probe.json or PROJECT.md. "
                             "Create one with novelty-probe init <folder> and run commands inside it, or pass --root.", d=here))


def rel(path, root=None):
    """项目内 → 相对路径（正斜杠）；项目外 → 绝对路径。"""
    p = Path(path).resolve()
    root = Path(root or PACKAGE_ROOT).resolve()
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)
