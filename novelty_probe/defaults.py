"""内置默认值（纯数据）：面、标注取值、证据表列名别名、版本识别词表、停用词。

novelty-probe.json 可以覆盖这些值（见 novelty_probe/config.py）；这里是没有配置文件时的取值，也是唯一的定义处：
config.DEFAULTS 与 scripts/textmatch.py 都从这里取，避免两处各写一份。

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
    "authors": ["作者", "Authors", "authors"],
    "year": ["年份", "Year", "year"],
    "title": ["题目", "Title", "title"],
    "id": ["DOI/arXiv"],
    "verified": ["verified"],
}
# 渲染证据表时各列的表头（facet 列用 FACETS 的标签）
COLUMN_HEADERS = {
    "rank": {"zh": "rank", "en": "rank"},
    "authors": {"zh": "作者", "en": "Authors"},
    "year": {"zh": "年份", "en": "Year"},
    "title": {"zh": "题目", "en": "Title"},
    "id": {"zh": "DOI/arXiv", "en": "DOI/arXiv"},
    "verified": {"zh": "verified", "en": "verified"},
}

# ---- 版本识别（同一研究的预印本与正式发表版本；scripts/textmatch.py 的 VersionRules） ----
# 预印本平台的 DOI 前缀：arXiv、bioRxiv/medRxiv、Research Square、SSRN、OSF 系列、TechRxiv、Preprints.org、ChemRxiv、Authorea、ESSOAr
PREPRINT_DOI_PREFIXES = [
    "10.48550/arxiv.", "10.1101/", "10.21203/rs.", "10.2139/ssrn.", "10.31219/", "10.31234/", "10.31235/",
    "10.31222/", "10.31224/", "10.31237/", "10.36227/techrxiv", "10.20944/preprints", "10.26434/chemrxiv",
    "10.22541/au.", "10.1002/essoar.",
]
# 出处名中含这些词（不区分大小写）即视为预印本
PREPRINT_VENUES = [
    "arxiv", "biorxiv", "medrxiv", "ssrn", "research square", "preprints.org", "preprint.org", "osf preprints",
    "psyarxiv", "socarxiv", "techrxiv", "chemrxiv", "authorea", "essoar",
]
# 数据仓储的 DOI 前缀：Zenodo、figshare、IEEE DataPort、Dryad、Mendeley Data、Harvard Dataverse、ICPSR
DATA_DOI_PREFIXES = ["10.5281/", "10.6084/", "10.21227/", "10.5061/", "10.17632/", "10.7910/", "10.3886/"]
YEAR_WINDOW = 3        # 同一研究的两个版本最多相差几年
MIN_TITLE_WORDS = 5    # 标题至少几个词才参与"按标题识别版本"

# ---- 与种子文献的内容相似度（snowball.py）中去掉的词 ----
STOPWORDS = """
a about above after again against all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here
hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of
off on once only or other our ours ourselves out over own same she should so some such than that the their
theirs them themselves then there these they this those through to too under until up very was we were what
when where which while who whom why will with would you your yours yourself yourselves via within without
however thus whether among across upon may might must shall us one two three new using use used based
study studies paper research results result findings show shows shown find found suggest suggests provide
provides propose proposes approach approaches analysis analyze examine examines investigate investigates
""".split()


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
