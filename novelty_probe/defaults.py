"""默认的面（facets）定义与证据表列名别名。阶段 2 由 novelty-probe.json 接管；这里是没有配置文件时的默认值。

每个面有一个稳定的 key（与 facets/facets.md、queries.json 的 facets_used 一致）和中英文标签；
脚本识别证据表的列时接受任一语言的标签。
"""

FACETS = [
    {"key": "research_question", "label": {"zh": "研究问题", "en": "Research question"}},
    {"key": "mechanism", "label": {"zh": "作用机制", "en": "Mechanism"}},
    {"key": "context", "label": {"zh": "研究情境", "en": "Context"}},
    {"key": "data_method", "label": {"zh": "数据与方法", "en": "Data and methods"}},
    {"key": "expected_findings", "label": {"zh": "预期发现", "en": "Expected findings"}},
]
LABELS = ["overlap", "differ", "unknown"]
COLUMNS = {
    "rank": ["rank"],
    "title": ["题目", "Title", "title"],
    "id": ["DOI/arXiv"],
    "verified": ["verified"],
}


def facet_labels(facets=None):
    """{面的 key: 该面所有语言的标签列表}。"""
    return {f["key"]: list(f["label"].values()) for f in (facets or FACETS)}


def facet_columns(cols, facets=None):
    """证据表的列名列表 → {面的 key: 列下标}；接受任一语言的标签。没找到的面不在结果里。"""
    out = {}
    for key, labels in facet_labels(facets).items():
        for label in labels:
            if label in cols:
                out[key] = cols.index(label)
                break
    return out


def find_column(cols, name, columns=None):
    """按别名找列下标；找不到返回 None。"""
    for alias in (columns or COLUMNS)[name]:
        if alias in cols:
            return cols.index(alias)
    return None
