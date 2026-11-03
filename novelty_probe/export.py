"""导出 RIS：文献管理软件（Zotero、EndNote、Mendeley 等）通用的导入格式。值都取自检索结果（PROJECT.md 规则 2）。

每条记录：TY（类型）→ TI 题目 → AU 作者（每位一行）→ PY 年份 → T2 出处 → DO DOI → UR 链接 → AB 摘要 → KW 标注
→ N1 来源说明 → ID 合并编号 → ER。类型：有正式发表 DOI 的记为 JOUR；只有预印本 DOI 或 arXiv ID 的记为 UNPB；
两者都没有的记为 GEN。文件用带 BOM 的 UTF-8、CRLF 换行（EndNote 与 Zotero 都能读；.gitattributes 不改换行）。
"""
from .io import atomic_write_text
from .text import DEFAULT_RULES, norm_doi


def _one_line(value):
    return " ".join(str(value).split())


def ris_type(x, rules=None):
    rules = rules or DEFAULT_RULES
    if x.get("doi") and not rules.preprint_doi.match(norm_doi(x["doi"]) or ""):
        return "JOUR"
    if x.get("doi") or x.get("arxiv_id"):
        return "UNPB"
    return "GEN"


def ris_record(x, keywords=(), note=None, rules=None):
    """一条记录（合并记录的字段：title, authors, n_authors, year, venue, doi, arxiv_id, abstract, merged_id）→ RIS 行列表。"""
    lines = [("TY", ris_type(x, rules))]
    if x.get("title"):
        lines.append(("TI", x["title"]))
    for name in x.get("authors") or []:
        lines.append(("AU", name))
    if x.get("year"):
        lines.append(("PY", x["year"]))
    if x.get("venue"):
        lines.append(("T2", x["venue"]))
    if x.get("doi"):
        lines.append(("DO", x["doi"]))
        lines.append(("UR", f"https://doi.org/{x['doi']}"))
    if x.get("arxiv_id"):
        lines.append(("UR", f"https://arxiv.org/abs/{x['arxiv_id']}"))
    if x.get("abstract"):
        lines.append(("AB", x["abstract"]))
    for kw in keywords:
        lines.append(("KW", kw))
    notes = [note] if note else []
    if x.get("n_authors") and len(x.get("authors") or []) < x["n_authors"]:
        notes.append(f"first {len(x['authors'])} of {x['n_authors']} authors")
    if notes:
        lines.append(("N1", "; ".join(notes)))
    if x.get("merged_id"):
        lines.append(("ID", x["merged_id"]))
    out = [f"{tag}  - {_one_line(value)}" for tag, value in lines if _one_line(value)]
    out.append("ER  - ")
    return out


def provenance_note(x):
    """合并记录的来源说明：来自哪些检索式与来源、RRF 名次分数、合并依据。"""
    parts = ["novelty-probe"]
    if x.get("query_ids"):
        parts.append("queries " + ",".join(x["query_ids"]))
    if x.get("sources"):
        parts.append("sources " + ",".join(x["sources"]))
    if x.get("rrf") is not None:
        parts.append(f"rrf {x['rrf']}")
    if x.get("dedupe_rules"):
        parts.append("dedupe " + ",".join(x["dedupe_rules"]))
    return " | ".join(parts)


def to_ris(records, keywords=None, notes=None, rules=None):
    """多条记录 → RIS 文本（记录之间空一行）。keywords / notes：与 records 同序的列表，可省略。"""
    blocks = []
    for i, x in enumerate(records):
        kw = (keywords[i] if keywords else None) or ()
        note = notes[i] if notes else provenance_note(x)
        blocks.append("\r\n".join(ris_record(x, kw, note, rules)))
    return "\r\n\r\n".join(blocks) + ("\r\n" if blocks else "")


def write_ris(path, records, keywords=None, notes=None, rules=None):
    atomic_write_text(path, "﻿" + to_ris(records, keywords, notes, rules))


def parse_ris(text):
    """读回 RIS（测试与核对用）：[{标签: [值, …]}]。"""
    out, cur = [], None
    for line in text.lstrip("﻿").splitlines():
        if len(line) < 6 or line[2:6] != "  - ":
            continue
        tag, value = line[:2], line[6:]
        if tag == "TY":
            cur = {}
        if cur is None:
            continue
        if tag == "ER":
            out.append(cur)
            cur = None
            continue
        cur.setdefault(tag, []).append(value)
    return out
