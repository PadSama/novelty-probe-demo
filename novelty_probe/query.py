"""检索式：解析为语法树、规范写法、在标题与摘要上求值（阶段 3）。

写法（与 AGENTS.md 一致）：
- 顶层用 AND 连接若干组；组是单个检索词，或括号内用 OR 连接的检索词；
- 排除组写成 AND NOT x 或 AND NOT (x OR y)，放在包含组之后；
- 检索词：单词、英文双引号短语、词尾带 * 的截断词；
- 运算符必须大写；不支持嵌套括号、括号内的 AND、括号外的 OR、逗号、未配对的引号；括号内的词之间必须写 OR，组与组之间必须写 AND。
解析一次得到 Query：语法树（组、词）加上原文与记号序列。各数据源从同一个 Query 序列化（novelty_probe/sources/）：
OpenAlex 照原文发送、S2 按记号改写，两者都与阶段 3 之前逐字节相同（tests/fixtures/query_golden.json）。
错误为 QueryError：code 是固定的错误码（Q1xx 语法，Q2xx 某个数据源的序列化），pos 是出错位置（字符下标，从 0 起）。
"""
import re
from dataclasses import dataclass
from functools import lru_cache

from .i18n import t

OPERATORS = ("AND", "OR", "NOT")
# 记号：成对引号的短语 | 括号 | 单独的引号（未配对，报错用） | 其他连续的非空白字符
_TOKEN_RE = re.compile(r'"[^"]*"|[()]|"|[^\s()"]+')


@dataclass(frozen=True)
class Term:
    raw: str      # 原始记号（短语带引号）：与旧接口 parse_query() 返回的字符串相同
    kind: str     # word / phrase / prefix（截断词）
    text: str     # 短语去掉引号；截断词保留 *
    pos: int


@dataclass(frozen=True)
class Group:
    terms: tuple
    negated: bool = False
    parenthesized: bool = False
    pos: int = 0

    @property
    def raws(self):
        return [term.raw for term in self.terms]


@dataclass(frozen=True)
class Query:
    raw: str
    groups: tuple     # 按原文顺序
    tokens: tuple     # ((记号, 位置), ...)

    @property
    def include(self):
        return [g for g in self.groups if not g.negated]

    @property
    def exclude(self):
        return [g for g in self.groups if g.negated]

    def lists(self):
        """旧接口的形状：([[记号, …], …], [[记号, …], …])，即（包含组，排除组），短语带引号。"""
        return [g.raws for g in self.include], [g.raws for g in self.exclude]

    def terms(self, negated=False):
        return [term for g in self.groups if g.negated == negated for term in g.terms]

    def canonical(self):
        """规范写法：多词组加括号，组之间用 AND，排除组写成 NOT (…)。解析规范写法得到同一棵语法树。"""
        parts = []
        for g in self.groups:
            body = " OR ".join(g.raws)
            if len(g.terms) > 1 or g.parenthesized:
                body = f"({body})"
            parts.append(f"NOT {body}" if g.negated else body)
        return " AND ".join(parts)


class QueryError(ValueError):
    """检索式错误：code（固定错误码）、pos（字符下标）、message（不含错误码与位置的说明）。"""

    def __init__(self, code, key, pos=None, **kw):
        self.code, self.key, self.pos = code, key, pos
        self.message = t(key, **kw)
        where = t("query.where", code=code, col=pos + 1) if pos is not None else t("query.where_code", code=code)
        super().__init__(self.message + where)


def _term(tok, pos):
    if tok.startswith('"'):
        return Term(tok, "phrase", tok[1:-1], pos)
    if tok.endswith("*"):
        return Term(tok, "prefix", tok, pos)
    return Term(tok, "word", tok, pos)


def _check_token(tok, pos):
    if tok == '"':
        raise QueryError("Q112", "query.unbalanced_quote", pos)
    if tok == '""':
        raise QueryError("Q113", "query.empty_phrase", pos)
    if "," in tok:
        raise QueryError("Q111", "query.comma", pos + tok.index(","))
    if tok.upper() in OPERATORS:
        raise QueryError("Q107", "query.lowercase_operator", pos, tok=tok, upper=tok.upper())
    if not tok.startswith('"'):
        if tok[0] in "-!":
            raise QueryError("Q108", "query.negation_prefix", pos, ch=tok[0], tok=tok)
        if "*" in tok and (tok == "*" or tok.count("*") > 1 or not tok.endswith("*")):
            raise QueryError("Q114", "query.truncation_position", pos + tok.index("*"), tok=tok)


@lru_cache(maxsize=1024)
def parse(text):
    """检索式 → Query；不合写法时抛 QueryError（遇到的第一处错误）。"""
    tokens = tuple((m.group(0), m.start()) for m in _TOKEN_RE.finditer(text))
    groups, cur = [], []
    depth, open_pos, negate, paren, group_pos = 0, None, False, False, 0
    last = None      # 上一个记号的类别：None（开头）、AND、NOT、(、OR、term、)

    def close(pos):
        nonlocal cur, negate, paren
        if not cur:
            raise QueryError("Q109", "query.empty_group", pos)
        groups.append(Group(tuple(cur), negate, paren, group_pos))
        cur, negate, paren = [], False, False

    for tok, pos in tokens:
        if tok == "(":
            if depth:
                raise QueryError("Q101", "query.nested", pos)
            if last in ("term", ")"):
                raise QueryError("Q116", "query.missing_and", pos)
            depth, open_pos, paren, last = 1, pos, True, "("
            if not cur:
                group_pos = pos
        elif tok == ")":
            if not depth:
                raise QueryError("Q102", "query.unbalanced", pos)
            if last == "(":
                raise QueryError("Q109", "query.empty_group", pos)
            if last == "OR":
                raise QueryError("Q117", "query.dangling_or", pos)
            depth, last = 0, ")"
        elif tok == "AND":
            if depth:
                raise QueryError("Q103", "query.and_in_group", pos)
            if last in (None, "AND", "NOT"):
                raise QueryError("Q109", "query.empty_group", pos)
            close(pos)
            last = "AND"
        elif tok == "OR":
            if not depth:
                raise QueryError("Q104", "query.or_outside", pos)
            if last in ("(", "OR"):
                raise QueryError("Q117", "query.dangling_or", pos)
            last = "OR"
        elif tok == "NOT":
            if last is None:
                raise QueryError("Q105", "query.not_first", pos)
            if depth or last != "AND":
                raise QueryError("Q106", "query.not_position", pos)
            negate, last = True, "NOT"
        else:
            _check_token(tok, pos)
            if last in ("term", ")"):
                raise QueryError("Q115" if depth else "Q116", "query.missing_or" if depth else "query.missing_and", pos)
            if not cur and not depth:
                group_pos = pos
            cur.append(_term(tok, pos))
            last = "term"
    end = len(text)
    if depth:
        raise QueryError("Q102", "query.unbalanced", open_pos)
    if last in (None, "AND", "NOT"):
        raise QueryError("Q109", "query.empty_group", end)
    close(end)
    if not any(not g.negated for g in groups):
        raise QueryError("Q110", "query.no_include", 0)
    return Query(text, tuple(groups), tokens)


def evaluate(query, doc, ignore=()):
    """标题 + 摘要（text.Doc）是否满足检索式：每个包含组至少命中一个词，且不命中任何排除词。"""
    from .text import query_match
    q = parse(query) if isinstance(query, str) else query
    include, exclude = q.lists()
    return query_match(include, doc, exclude, ignore)


def caret(text, pos):
    """在检索式下一行用 ^ 标出出错位置（dry-run 打印用）。"""
    return " " * max(0, pos) + "^"
