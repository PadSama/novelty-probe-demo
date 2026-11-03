"""各数据源共用的记录整理：DOI、arXiv ID、摘要。值直接取自 API 返回，只做格式整理。"""
import html
import re

ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.I)
ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(.+?)(?:\.pdf)?(?:[?#].*)?$", re.I)
_TAG_RE = re.compile(r"<[^>]+>")


def clean_doi(doi):
    if not doi:
        return None
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I) or None


def clean_arxiv(aid):
    if not aid:
        return None
    aid = re.sub(r"^arxiv:", "", aid.strip(), flags=re.I)
    return re.sub(r"v\d+$", "", aid) or None


def rebuild_abstract(inverted):
    """OpenAlex 的倒排索引 → 摘要原文。"""
    if not inverted:
        return None
    words = sorted((pos, w) for w, positions in inverted.items() for pos in positions)
    return " ".join(w for _, w in words)


def strip_markup(text):
    """去掉 XML / HTML 标签（如 Crossref 的 JATS 标签）与实体，合并空白。先解码实体再去标签：
    Crossref 的题目里有转义过的标签（如 "&lt;strong&gt;"），解码后才认得出是标签。"""
    if not text:
        return None
    return " ".join(_TAG_RE.sub(" ", html.unescape(text)).split()) or None
