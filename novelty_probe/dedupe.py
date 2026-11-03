"""去重：同一篇文献的多条原始记录并成一组。每个合并决定都记规则编号；拿不准的情况只记录原因、保持分开，不设人工复核。

两步：
1. 按标识符：DOI 相同（D1）、预印本平台的版本 DOI 去掉版本后缀后相同（D2）、arXiv ID 相同（D3）；
2. 按版本：在标识符分组之间比较题目（novelty_probe/text.py 的 version_decision_coded），作者作为证据：
   D4  规范化题目相同，且通过各项检查（见 RULES）；但两边都有可比的作者名、却没有一个共同的名字时不合并（R7）；
   D5  题目几乎相同、通过同样的检查，且有共同的作者：至少两个共同的姓，一方只有一位作者时一个即可。
   作者名去重音、小写，只比较两个字母以上的拉丁字母词（首字母缩写不算）；一方的作者名没有这样的词（如只用汉字书写）时，
   作者不作为证据：D4 照常合并，D5 不合并（R6）。
   其余疑似情况不合并，记下原因（R1–R8）。一个合并组最多含 max_groups 个标识符分组（R8），防止连锁误并。
旧数据没有作者，只会用到 D1–D4 与 R1–R6，结果与阶段 3 相同。
"""
from itertools import combinations

from .record import doi_key
from .text import abstracts_similar, norm_doi, version_decision_coded, version_summary

RULES = {
    "D1": "same DOI (case, URL query and landing-page suffix ignored)",
    "D2": "same preprint DOI apart from its version suffix (OSF _vN, TechRxiv /vN, Research Square /vN)",
    "D3": "same arXiv ID (version ignored)",
    "D4": "same normalized title (publication-status notes stripped, >= min_title_words words), no notice/variant "
          "word on one side only, no two different non-preprint DOIs, no data-repository DOI, year gap <= year_window, "
          "abstract word Jaccard >= 0.5 when both have abstracts, and a common author name when both have comparable names",
    "D5": "near-identical titles (difflib >= 0.90 and word Jaccard >= 0.80, or one contained in the other), the D4 "
          "checks, and shared authors (two common surnames, or one when either side lists a single author)",
    "R1": "kept separate: same title, but a notice/variant word on one side only",
    "R2": "kept separate: same title, but two different non-preprint DOIs",
    "R3": "kept separate: same title, but a data-repository DOI",
    "R4": "kept separate: same title, but years differ by more than year_window",
    "R5": "kept separate: same title, but abstracts differ",
    "R6": "kept separate: near-identical titles without enough author evidence",
    "R7": "kept separate: same title, but no author name in common (both sides have names in Latin letters)",
    "R8": "kept separate: the merged group would exceed max_cluster_groups identifier groups",
}
_REVIEW_RULE = {"notice_variant": "R1", "two_pub_dois": "R2", "data_doi": "R3", "year_gap": "R4", "abstracts_differ": "R5"}


def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def id_groups(recs):
    """按 DOI（规范化）与 arXiv ID 判重。返回 (每条记录所属组的根, 合并事件 [(i, j, 规则)])。"""
    parent = list(range(len(recs)))
    seen, links = {}, []
    for i, r in enumerate(recs):
        keys = ([("doi", doi_key(r["doi"]), norm_doi(r["doi"]))] if r["doi"] else []) + \
               ([("arxiv", r["arxiv_id"].strip().lower(), None)] if r["arxiv_id"] else [])
        for kind, key, exact in keys:
            if (kind, key) in seen:
                j, exact_j = seen[(kind, key)]
                a, b = _find(parent, j), _find(parent, i)
                if a != b:
                    parent[max(a, b)] = min(a, b)
                    links.append((j, i, "D3" if kind == "arxiv" else ("D1" if exact == exact_j else "D2")))
            else:
                seen[(kind, key)] = (i, exact)
    return [_find(parent, i) for i in range(len(recs))], links


def _shared_surnames(a, b):
    need = 1 if min(a["author_count"], b["author_count"]) == 1 else 2
    return len(a["surnames"] & b["surnames"]) >= need


def _no_conflicts(a, b, rules):
    if a["pub_dois"] and b["pub_dois"] and not set(a["pub_dois"]) & set(b["pub_dois"]):
        return False
    if any(rules.data_doi.match(d) for d in a["dois"] + b["dois"]):
        return False
    return a["variant"] == b["variant"] and abstracts_similar(a, b)


def decide(a, b, rules):
    """两个标识符分组（version_summary 的结果）→ (merge / keep / no, 规则编号, 原因)。keep：疑似同一篇，但保持分开。"""
    verdict, code, reason = version_decision_coded(a, b, rules)
    comparable = bool(a["name_tokens"]) and bool(b["name_tokens"])   # 两边都有可比的作者名；否则作者不作为证据
    if verdict == "merge":
        if comparable and not (a["name_tokens"] & b["name_tokens"]):
            return "keep", "R7", "same title, but no author name in common"
        return "merge", "D4", reason
    if verdict == "review":
        if code == "near_identical":
            if comparable and _shared_surnames(a, b) and _no_conflicts(a, b, rules):
                return "merge", "D5", reason + "; shared authors"
            return "keep", "R6", reason
        return "keep", _REVIEW_RULE[code], reason
    return "no", None, reason


def link_versions(recs, roots, rules, max_groups=6):
    """在标识符分组之间识别同一研究的不同版本。
    返回 (每条记录的最终根, 合并 [(根a, 根b, 规则, 原因)], 保持分开的疑似情况 [(根a, 根b, 规则, 原因)])。
    分组按根的编号依次两两比较；合并组的大小以标识符分组计，超过 max_groups 的合并不做（R8）。"""
    members = {}
    for i, r in enumerate(roots):
        members.setdefault(r, []).append(i)
    summ = {r: version_summary([recs[i] for i in idx], rules=rules) for r, idx in members.items()}
    parent = {r: r for r in members}
    size = {r: 1 for r in members}
    merges, kept = [], []
    for a, b in combinations(sorted(members), 2):
        verdict, rule, reason = decide(summ[a], summ[b], rules)
        if verdict == "merge":
            ra, rb = _find(parent, a), _find(parent, b)
            if ra != rb and size[ra] + size[rb] > max_groups:
                kept.append((a, b, "R8", f"merged group would exceed {max_groups} identifier groups"))
                continue
            merges.append((a, b, rule, reason))
            if ra != rb:
                keep_root, gone = min(ra, rb), max(ra, rb)
                parent[gone] = keep_root
                size[keep_root] += size.pop(gone)
        elif verdict == "keep":
            kept.append((a, b, rule, reason))
    final = [_find(parent, r) for r in roots]
    kept = [(a, b, rule, why) for a, b, rule, why in kept if _find(parent, a) != _find(parent, b)]
    return final, merges, kept


def rules_by_group(roots_all, roots_id, id_links, merges):
    """每个最终分组用到的合并规则：{最终根: [规则, …]}（排序后）。"""
    out = {}
    for i, _, rule in id_links:
        out.setdefault(roots_all[i], set()).add(rule)
    for a, _, rule, _ in merges:
        out.setdefault(roots_all[a], set()).add(rule)
    return {k: sorted(v) for k, v in out.items()}
