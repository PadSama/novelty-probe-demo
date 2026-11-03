"""数据源注册表。加一个数据源：在本目录写一个模块（实现 base.Source），在 REGISTRY 里登记，再录一份测试件；
search.py、merge.py、qa.py、compare.py 都从这里取数据源与文件名前缀，不用改动。
登记的顺序就是合并时的来源顺序（决定标题等字段优先取哪个来源的值），新数据源加在末尾，已有结果的合并不受影响。"""
from .base import Context, Source
from .crossref import Crossref
from .openalex import OpenAlex
from .semanticscholar import SemanticScholar

REGISTRY = {s.name: s for s in (OpenAlex(), SemanticScholar(), Crossref())}
NAMES = list(REGISTRY)      # 同一个列表对象供各脚本引用：登记新数据源后它们立即可见


def register(source):
    """登记一个数据源（加在末尾）；同名的替换原有登记。"""
    if source.name not in REGISTRY:
        NAMES.append(source.name)
    REGISTRY[source.name] = source
    return source


def unregister(name):
    REGISTRY.pop(name, None)
    if name in NAMES:
        NAMES.remove(name)


def enabled(cfg):
    """配置中启用的数据源（按登记顺序）。"""
    srcs = (cfg or {}).get("sources") or {}
    return [n for n in NAMES if (srcs.get(n) or {}).get("enabled", REGISTRY[n].enabled_by_default)]


__all__ = ["Context", "Source", "REGISTRY", "NAMES", "enabled", "register", "unregister"]
