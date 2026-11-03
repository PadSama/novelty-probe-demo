"""文本匹配（只用标准库），供检索、合并、质量检查、引文追踪、补摘要与证据检查共用。

- porter_stem()：Porter（1980）词干还原的独立实现，规则与 Snowball 的 "porter" 一致；
- tokenize() / term_in()：在标题 + 摘要中按词干匹配检索词（短语、截断词、单词）；
- query_match()：判断一段文本是否满足检索式（含 NOT 组）；
- BM25：按检索词给一组文本打相关度分；
- tfidf_vectors() / centroid() / cosine()：与种子文献的内容相似度（引文追踪的排序）；
- title_key() / version_title_match() / VersionRules：识别同一研究的不同版本（预印本与正式发表）。
阶段 3 从 scripts/textmatch.py 移入本包；scripts/textmatch.py 保留为转发，旧的 import 照常可用。
"""
import html
import math
import re
import unicodedata
from difflib import SequenceMatcher

from . import defaults as _D

# ---------- Porter 词干还原 ----------

_VOWELS = set("aeiou")


def _is_consonant(w, i):
    ch = w[i]
    if ch in _VOWELS:
        return False
    if ch == "y":
        return i == 0 or not _is_consonant(w, i - 1)
    return True


def _measure(stem):
    """[C](VC)^m[V] 中的 m。"""
    m, i, n = 0, 0, len(stem)
    while i < n and _is_consonant(stem, i):
        i += 1
    while i < n:
        while i < n and not _is_consonant(stem, i):
            i += 1
        if i >= n:
            break
        while i < n and _is_consonant(stem, i):
            i += 1
        m += 1
    return m


def _has_vowel(stem):
    return any(not _is_consonant(stem, i) for i in range(len(stem)))


def _ends_double_consonant(w):
    return len(w) >= 2 and w[-1] == w[-2] and _is_consonant(w, len(w) - 1)


def _ends_cvc(w):
    if len(w) < 3:
        return False
    return (_is_consonant(w, len(w) - 3) and not _is_consonant(w, len(w) - 2)
            and _is_consonant(w, len(w) - 1) and w[-1] not in "wxy")


def _replace(w, rules, condition):
    """按规则表找最长匹配的后缀；条件成立就替换。返回新词（无匹配或条件不成立时原样返回）。"""
    for suffix, repl in rules:
        if w.endswith(suffix):
            stem = w[: len(w) - len(suffix)]
            return stem + repl if condition(stem) else w
    return w


_STEP2 = sorted([("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"), ("izer", "ize"),
                 ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"), ("ousli", "ous"),
                 ("ization", "ize"), ("ation", "ate"), ("ator", "ate"), ("alism", "al"), ("iveness", "ive"),
                 ("fulness", "ful"), ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble")],
                key=lambda r: -len(r[0]))
_STEP3 = sorted([("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"), ("ical", "ic"),
                 ("ful", ""), ("ness", "")], key=lambda r: -len(r[0]))
_STEP4 = sorted(["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent",
                 "ion", "ou", "ism", "ate", "iti", "ous", "ive", "ize"], key=lambda s: -len(s))


def porter_stem(word):
    w = word.lower()
    if not w:
        return w
    # Step 1a
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("ss"):
        pass
    elif w.endswith("s"):
        w = w[:-1]
    # Step 1b
    if w.endswith("eed"):
        if _measure(w[:-3]) > 0:
            w = w[:-1]
    else:
        for suf in ("ed", "ing"):
            if w.endswith(suf) and _has_vowel(w[: -len(suf)]):
                w = w[: -len(suf)]
                if w.endswith(("at", "bl", "iz")):
                    w += "e"
                elif _ends_double_consonant(w) and w[-1] not in "lsz":
                    w = w[:-1]
                elif _measure(w) == 1 and _ends_cvc(w):
                    w += "e"
                break
    # Step 1c
    if w.endswith("y") and _has_vowel(w[:-1]):
        w = w[:-1] + "i"
    # Steps 2 and 3
    w = _replace(w, _STEP2, lambda s: _measure(s) > 0)
    w = _replace(w, _STEP3, lambda s: _measure(s) > 0)
    # Step 4
    for suf in _STEP4:
        if w.endswith(suf):
            stem = w[: -len(suf)]
            if _measure(stem) > 1 and (suf != "ion" or stem.endswith(("s", "t"))):
                w = stem
            break
    # Step 5a
    if w.endswith("e"):
        stem = w[:-1]
        m = _measure(stem)
        if m > 1 or (m == 1 and not _ends_cvc(stem)):
            w = stem
    # Step 5b
    if _measure(w) > 1 and _ends_double_consonant(w) and w.endswith("l"):
        w = w[:-1]
    return w


# ---------- 分词与检索词匹配 ----------

_TAG_RE = re.compile(r"<[^>]+>")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_cache = {}


def tokenize(text):
    """小写字母数字词；去 HTML 标签与实体。"""
    return _TOKEN_RE.findall(html.unescape(_TAG_RE.sub(" ", text or "")).lower())


def stem(word):
    s = _cache.get(word)
    if s is None:
        s = _cache[word] = porter_stem(word)
    return s


class Doc:
    """预处理后的文本：原词序列与词干序列。"""

    def __init__(self, *texts):
        self.raw = [t for text in texts for t in tokenize(text)]
        self.stems = [stem(t) for t in self.raw]


def term_positions(term, doc):
    """检索词在文中出现的起始位置。短语按词干逐词连续匹配；以 * 结尾的截断词按原词前缀匹配。"""
    t = term.strip().strip('"')
    if t.endswith("*"):
        prefix = t[:-1].lower()
        return [i for i, w in enumerate(doc.raw) if w.startswith(prefix)]
    words = [stem(w) for w in tokenize(t)]
    n = len(words)
    if not n:
        return []
    return [i for i in range(len(doc.stems) - n + 1) if doc.stems[i:i + n] == words]


def term_in(term, doc, ignore=()):
    """检索词是否出现；ignore 中的短语所覆盖的位置不算（如 narrow 出现在 "narrow AI" 里时）。"""
    pos = term_positions(term, doc)
    if not pos or not ignore:
        return bool(pos)
    blocked = set()
    for phrase in ignore:
        n = len(tokenize(phrase.strip('"')))
        for p in term_positions(phrase, doc):
            blocked.update(range(p, p + n))
    return any(p not in blocked for p in pos)


def query_match(include_groups, doc, exclude_groups=(), ignore=()):
    """每个包含组至少命中一个词，且没有任何排除组命中。"""
    if any(any(term_in(t, doc) for t in g) for g in exclude_groups):
        return False
    return all(any(term_in(t, doc, ignore) for t in g) for g in include_groups)


def groups_matched(groups, doc, ignore=()):
    """命中的组数（每组至少命中一个词即算命中）。"""
    return sum(any(term_in(t, doc, ignore) for t in g) for g in groups)


# ---------- BM25 ----------

class BM25:
    """在给定文本集合上计算 BM25（k1=1.2，b=0.75）。检索词可以是短语，按短语出现次数计词频。"""

    def __init__(self, docs, terms, k1=1.2, b=0.75):
        self.docs, self.terms, self.k1, self.b = docs, list(dict.fromkeys(terms)), k1, b
        self.avgdl = (sum(len(d.stems) for d in docs) / len(docs)) if docs else 0.0
        self.tf = [{t: len(term_positions(t, d)) for t in self.terms} for d in docs]
        n = len(docs)
        self.idf = {}
        for t in self.terms:
            df = sum(1 for tf in self.tf if tf[t])
            self.idf[t] = math.log(1 + (n - df + 0.5) / (df + 0.5))

    def score(self, i, ignore=()):
        d, tf, s = self.docs[i], self.tf[i], 0.0
        dl = len(d.stems) or 1
        for t in self.terms:
            f = tf[t]
            if f and ignore and not term_in(t, d, ignore):
                f = 0
            if f:
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
        return s


# ---------- 与种子文献的相似度（TF-IDF 余弦） ----------

STOPWORDS = frozenset(_D.STOPWORDS)   # 默认停用词；配置 textmatch.stopwords 可替换或追加


def content_terms(doc, stopwords=None):
    """用于相似度的词干：去掉停用词（默认 STOPWORDS）、单字符词和纯数字。"""
    sw = STOPWORDS if stopwords is None else stopwords
    return [s for w, s in zip(doc.raw, doc.stems) if w not in sw and len(w) > 1 and not w.isdigit()]


def tfidf_vectors(term_lists):
    """每篇一个 L2 归一化的 TF-IDF 向量（dict）。tf = 1 + log(次数)，idf = log((N+1)/(df+1)) + 1。"""
    n = len(term_lists)
    df = {}
    for terms in term_lists:
        for t in set(terms):
            df[t] = df.get(t, 0) + 1
    vecs = []
    for terms in term_lists:
        counts = {}
        for t in terms:
            counts[t] = counts.get(t, 0) + 1
        v = {t: (1 + math.log(c)) * (math.log((n + 1) / (df[t] + 1)) + 1) for t, c in counts.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / norm for t, x in v.items()})
    return vecs


def centroid(vecs):
    """若干个向量的平均（再归一化）。"""
    c = {}
    for v in vecs:
        for t, x in v.items():
            c[t] = c.get(t, 0.0) + x / len(vecs)
    norm = math.sqrt(sum(x * x for x in c.values())) or 1.0
    return {t: x / norm for t, x in c.items()}


def cosine(u, v):
    if len(u) > len(v):
        u, v = v, u
    return sum(x * v.get(t, 0.0) for t, x in u.items())


# ---------- 版本识别（同一研究的预印本与正式发表版本） ----------
# 规则参照 bib-dedupe、ASySD、Zotero、JabRef 等去重工具的做法与 preprint–publication 匹配研究，取保守的一侧：
# 标题规范化后完全相同才自动合并，其余疑似情况只标出供人工核对（见 merge.py）。

_TAG_OR_ENTITY_RE = re.compile(r"<[^>]+>")
# 末尾括注中只表示发表状态的说明：比较前去掉（最多两个），如 "(Just accepted by Nature, to be online soon)"
_STATUS_RE = re.compile(
    r"^\s*(?:just\s+)?accepted\b|\baccepted (?:by|at|in|for|to)\b|\bto appear\b|\bin press\b|\bforthcoming\b|"
    r"\bpublished (?:in|at|by|version)\b|\bcamera[- ]?ready\b|\bpre-?print\b|\bpost-?print\b|\b(?:to be )?online soon\b|"
    r"\bearly access\b|\bauthor'?s? (?:version|copy)\b|\baccepted (?:manuscript|version)\b|\bversion of record\b|"
    r"\bunder review\b|\bsubmitted (?:to|for)\b|\bworking paper\b|^\s*draft\s*$|^\s*v\d+\s*$|^\s*revised(?: version)?\s*$",
    re.I)
_TRAILING_GROUP_RE = re.compile(r"\s*[\(\[]([^()\[\]]*)[\)\]]\s*\.?\s*$")
# 关于另一篇文献的条目（读者来信、回复、更正、撤稿等）：不是同一研究的另一个版本
_NOTICE_START_RE = re.compile(
    r"^\s*(?:(?:re|reply|response|comment|commentary|correction|author correction|publisher correction|retraction note|"
    r"retraction|expression of concern|editorial expression of concern|matters arising|addendum|editorial)"
    r"\s*(?::|\bto\b|\bon\b|\bregarding\b)|(?:erratum|errata|corrigendum)\b|retracted\b)", re.I)
_NOTICE_ANY_RE = re.compile(r"[\(\[]\s*(?:retracted|retraction|withdrawn)\b", re.I)
# 内容不同的变体：扩展摘要、短文、补充材料、第 N 部分
_VARIANT_RE = re.compile(r"\b(?:extended (?:abstract|version)|full version|short paper|supplement\w*|part [ivx\d]+|"
                         r"abstract no)\b", re.I)
_NUM_RE = re.compile(r"\b(?:\d+|[ivx]+)\b")


def _prefix_re(prefixes):
    """DOI 前缀列表 → 从开头匹配的正则（不区分大小写）；空列表 → 永不匹配。"""
    if not prefixes:
        return re.compile(r"(?!)")
    return re.compile("^(?:" + "|".join(re.escape(p.lower()) for p in prefixes) + ")", re.I)


def _substring_re(words):
    """词列表 → 匹配其中任一子串的正则（不区分大小写）；空列表 → 永不匹配。"""
    if not words:
        return re.compile(r"(?!)")
    return re.compile("|".join(re.escape(w.lower()) for w in words), re.I)


class VersionRules:
    """版本识别用到的词表与阈值（配置 versions.*；默认值见 novelty_probe/defaults.py）。
    判定规则本身与顺序（version_decision）、摘要 Jaccard 0.5、标题相似度 0.9 / 0.8 不在配置里：它们变了结果就不可比。"""

    def __init__(self, preprint_doi_prefixes=None, preprint_venues=None, data_doi_prefixes=None,
                 year_window=None, min_title_words=None):
        self.preprint_doi = _prefix_re(_D.PREPRINT_DOI_PREFIXES if preprint_doi_prefixes is None else preprint_doi_prefixes)
        self.preprint_venue = _substring_re(_D.PREPRINT_VENUES if preprint_venues is None else preprint_venues)
        self.data_doi = _prefix_re(_D.DATA_DOI_PREFIXES if data_doi_prefixes is None else data_doi_prefixes)
        self.year_window = _D.YEAR_WINDOW if year_window is None else int(year_window)
        self.min_title_words = _D.MIN_TITLE_WORDS if min_title_words is None else int(min_title_words)

    @classmethod
    def from_config(cls, cfg):
        """cfg 是完整配置或其中的 versions 部分。"""
        v = cfg.get("versions", cfg)
        return cls(v["preprint_doi_prefixes"], v["preprint_venues"], v["data_doi_prefixes"],
                   v["year_window"], v["min_title_words"])

    def is_preprint_doi(self, doi):
        return bool(doi) and bool(self.preprint_doi.match(doi))


DEFAULT_RULES = VersionRules()
# 兼容旧名（默认规则）
PREPRINT_DOI_RE = DEFAULT_RULES.preprint_doi
PREPRINT_VENUE_RE = DEFAULT_RULES.preprint_venue
DATA_DOI_RE = DEFAULT_RULES.data_doi
YEAR_WINDOW = DEFAULT_RULES.year_window


def norm_doi(doi):
    """比较用的 DOI：小写；去掉解析器前缀、URL 查询串与落地页后缀（如 /full/html?utm_source=…）。"""
    if not doi:
        return None
    d = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", doi.strip().lower())
    d = re.split(r"[?#]", d)[0]
    return re.sub(r"/(?:full|abstract|pdf|epdf|html)(?:/html)?/?$", "", d) or None


def strip_status_notes(title):
    t = title or ""
    for _ in range(2):
        m = _TRAILING_GROUP_RE.search(t)
        if not m or _NOTICE_ANY_RE.search(m.group(0)) or _VARIANT_RE.search(m.group(1)) \
                or not _STATUS_RE.search(m.group(1)):
            break
        t = t[:m.start()]
    return t


def title_words(title):
    """比较用的标题词：去 HTML、去末尾的发表状态括注、去重音，小写，任何非字母数字字符都作分隔。"""
    t = strip_status_notes(html.unescape(_TAG_OR_ENTITY_RE.sub(" ", title or "")))
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return _WORD_RE.findall(t.lower())


def title_key(title):
    return " ".join(title_words(title))


def is_notice(title):
    return bool(_NOTICE_START_RE.search(title or "") or _NOTICE_ANY_RE.search(title or ""))


def is_variant(title):
    return bool(_VARIANT_RE.search(title or ""))


def _same_key(ka, kb):
    return ka == kb or ka.replace(" ", "") == kb.replace(" ", "")  # "problem-solving" 与 "problemsolving"


def version_title_match(a, b, min_words=6):
    """两个标题是否像同一研究的不同版本：规范化后相同（至少 min_words 个词），且都不是来信、回复、更正之类的条目。"""
    if not a or not b or is_notice(a) or is_notice(b):
        return False
    ka, kb = title_key(a), title_key(b)
    return _same_key(ka, kb) and len(ka.split()) >= min_words


_POSSESSIVE_RE = re.compile(r"['’]s\b", re.I)
_WORD_RE = re.compile(r"[^\W_]+")


def title_search_words(title, n=12):
    """在 OpenAlex 中按题目查找其他版本时用的检索词：去掉版本说明括注和所有格 's，
    只保留两个字符以上的词（OpenAlex 的分词会去掉所有格，单独的 s 会让检索落空）。"""
    t = _POSSESSIVE_RE.sub("", strip_status_notes(html.unescape(_TAG_OR_ENTITY_RE.sub(" ", title or "")))).lower()
    return [w for w in _WORD_RE.findall(t) if len(w) > 1][:n]


def version_summary(records, min_words=None, rules=None):
    """一组记录（同一 DOI / arXiv ID 已并在一起）用于版本比较的摘要信息。min_words 默认取 rules.min_title_words。"""
    rules = rules or DEFAULT_RULES
    min_words = rules.min_title_words if min_words is None else min_words
    titles = [r.get("title") for r in records if r.get("title")]
    dois = [norm_doi(r.get("doi")) for r in records if r.get("doi")]
    return {
        "keys": {k for k in (title_key(t) for t in titles) if len(k.split()) >= min_words},
        "min_words": min_words,
        "notice": any(is_notice(t) for t in titles),
        "variant": any(is_variant(t) for t in titles),
        "years": sorted({r["year"] for r in records if r.get("year")}),
        "dois": sorted(set(dois)),
        "pub_dois": sorted({d for d in dois if not rules.preprint_doi.match(d)}),
        "preprint": any(r.get("arxiv_id") or (r.get("venue") and rules.preprint_venue.search(r["venue"])) for r in records)
                    or any(rules.preprint_doi.match(d) for d in dois),
        "abstract": max((r.get("abstract") or "" for r in records), key=len),
    }


def _jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def version_decision(a, b, rules=None):
    """比较两组记录（version_summary 的结果），返回 (merge / review / no, 原因)。
    merge：规范化标题相同，且没有来信或变体标记只在一侧、没有两个不同的正式发表 DOI、都不是数据集 DOI、
           年份相差不超过 3 年、两边都有摘要时摘要词集合的 Jaccard ≥ 0.5；
    review：标题相同但不满足上述条件，或标题几乎相同（difflib ≥ 0.90 且词 Jaccard ≥ 0.80，或较短标题完整包含在较长标题中）；
    no：其余情况（含 "Re: <标题>" 这类关于另一篇文献的条目）。
    年份窗口（3）与数据仓储 DOI 前缀来自 rules（默认 DEFAULT_RULES）。"""
    rules = rules or DEFAULT_RULES
    window = rules.year_window
    if not a["keys"] or not b["keys"]:
        return "no", f"title shorter than {a.get('min_words', rules.min_title_words)} words"
    gap = min((abs(x - y) for x in a["years"] for y in b["years"]), default=0)
    one_sided_notice = a["notice"] != b["notice"]
    one_sided_variant = a["variant"] != b["variant"]
    if any(_same_key(x, y) for x in a["keys"] for y in b["keys"]):
        if one_sided_notice or one_sided_variant:
            return "review", "same title, but a notice/variant word appears on one side only"
        if a["pub_dois"] and b["pub_dois"] and not set(a["pub_dois"]) & set(b["pub_dois"]):
            return "review", "same title, but two different non-preprint DOIs"
        if any(rules.data_doi.match(d) for d in a["dois"] + b["dois"]):
            return "review", "same title, but one record has a data-repository DOI"
        if gap > window:
            return "review", f"same title, but years differ by more than {window}"
        if a["abstract"] and b["abstract"] and _jaccard(tokenize(a["abstract"]), tokenize(b["abstract"])) < 0.5:
            return "review", "same title, but abstracts differ (word Jaccard < 0.5)"
        return "merge", f"same normalized title; no DOI conflict; year gap <= {window}"
    ka, kb = min(a["keys"]), min(b["keys"])
    wa, wb = ka.split(), kb.split()
    jac = _jaccard(wa, wb)
    contained = (ka in kb or kb in ka) and min(len(wa), len(wb)) >= 6
    if not contained and jac < 0.8:   # 以下各分支都要求词 Jaccard ≥ 0.8 或包含关系，先排除，省去逐字符比较
        return "no", "titles differ"
    ratio = SequenceMatcher(None, ka, kb).ratio()
    if one_sided_notice and (contained or ratio >= 0.9):
        return "no", "a notice about the other record (Re:/reply/correction), not another version"
    na, nb = set(_NUM_RE.findall(ka)), set(_NUM_RE.findall(kb))
    if na and nb and na != nb:
        return "no", "different numbers (e.g. Part I vs Part II)"
    if ((ratio >= 0.9 and jac >= 0.8) or contained) and gap <= window:
        return "review", f"near-identical titles (ratio {ratio:.2f}, word Jaccard {jac:.2f})"
    return "no", "titles differ"
