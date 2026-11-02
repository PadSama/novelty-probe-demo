#!/usr/bin/env python3
"""novelty-probe 的文本匹配工具（只用标准库），供 qa.py、merge.py、snowball.py、enrich.py 共用。

- porter_stem()：Porter（1980）词干还原的独立实现，规则与 Snowball 的 "porter" 一致；
- tokenize() / phrase_in()：在标题 + 摘要中按词干匹配检索词（短语、截断词、单词）；
- query_match()：判断一段文本是否满足检索式（含 NOT 组）；
- BM25：按检索词给一组文本打相关度分；
- tfidf_vectors() / centroid() / cosine()：与种子文献的内容相似度（引文追踪的排序）；
- title_key() / version_title_match()：识别同一研究的不同版本（预印本与正式发表）。
"""
import html
import math
import re

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

STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here
hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of
off on once only or other our ours ourselves out over own same she should so some such than that the their
theirs them themselves then there these they this those through to too under until up very was we were what
when where which while who whom why will with would you your yours yourself yourselves via within without
however thus whether among across upon may might must shall us one two three new using use used based
study studies paper research results result findings show shows shown find found suggest suggests provide
provides propose proposes approach approaches analysis analyze examine examines investigate investigates
""".split())


def content_terms(doc):
    """用于相似度的词干：去掉停用词、单字符词和纯数字。"""
    return [s for w, s in zip(doc.raw, doc.stems) if w not in STOPWORDS and len(w) > 1 and not w.isdigit()]


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


# ---------- 版本识别 ----------

_NOTE_RE = re.compile(r"\s*[\(\[][^()\[\]]*(accepted|preprint|forthcoming|in press|to appear|under review|working paper|"
                      r"version|draft|online|published)[^()\[\]]*[\)\]]\s*$", re.I)
_NOT_SAME_WORK = re.compile(r"^\s*(re|reply|response|correction|corrigendum|erratum|retraction|retracted|comment|"
                            r"commentary|author correction|publisher correction|editorial expression of concern)\b"
                            r"|^\s*(reply|response|comment|correction) (to|on)\b", re.I)


_POSSESSIVE_RE = re.compile(r"['\u2019]s\b", re.I)
_WORD_RE = re.compile(r"[^\W_]+")


def _strip_title(title):
    return _NOTE_RE.sub("", html.unescape(_TAG_RE.sub(" ", title or "")))


def title_key(title):
    """用于比较的标题：去掉末尾的版本说明括注，统一引号与大小写，只保留字母数字词。"""
    return " ".join(tokenize(_strip_title(title)))


def title_search_words(title, n=12):
    """在 OpenAlex 中按题目查找其他版本时用的检索词：去掉版本说明括注和所有格 's，
    只保留两个字符以上的词（OpenAlex 的分词会去掉所有格，单独的 s 会让检索落空）。"""
    t = _POSSESSIVE_RE.sub("", _strip_title(title)).lower()
    return [w for w in _WORD_RE.findall(t) if len(w) > 1][:n]


def version_title_match(a, b, min_words=6):
    """两个标题是否像同一研究的不同版本：标题键完全相同（至少 min_words 个词），
    且都不是更正、回复、评论之类的独立条目。"""
    if not a or not b or _NOT_SAME_WORK.search(a) or _NOT_SAME_WORK.search(b):
        return False
    ka, kb = title_key(a), title_key(b)
    return ka == kb and len(ka.split()) >= min_words
