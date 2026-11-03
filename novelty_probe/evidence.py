"""证据表：JSON 是数据源（schema novelty-probe/evidence@1），Markdown 由它渲染。

为什么：Markdown 表格既给人看、又给脚本读写（verify 写 verified 列、snowball 取种子），列名、转义、表外文字都容易出错。
JSON 让脚本按字段读写，Markdown 只是视图。研究者或助手仍可以先写 Markdown，再用 import_markdown() 导入。

文档结构：
  {"schema": "novelty-probe/evidence@1",
   "meta": {"language", "facets", "labels", "columns": [{"key", "header"}], "results", "markdown",
            "imported_from", "updated_at", "rendered_sha256"},
   "sections": {"preamble": [行], "separator": "|---|…", "middle": [行], "postamble": [行], "final_newline": true},
   "rows": [{"rank", "merged_id", "authors", "year", "title", "doi", "arxiv_id", "labels": {面: 取值},
             "verified_text" 或 "verification", "rationale": {"note", "lines": [行]}, "cells_raw": {}, "extra": {}}],
   "orphan_rationale": [{"heading", "lines"}]}
  - sections：表外的文字（导入时原样保留）。没有 sections 的文档（直接写 JSON）渲染时用默认标题；
  - verification：verify.py 的结构化结果（novelty_probe/verification.py），渲染时按语言生成文字；
    verified_text：从 Markdown 导入、尚未用 JSON 核验过的 verified 列原文；
  - cells_raw：某列的原文与按字段重新生成的文字不同时保留原文（如 DOI/arXiv 列写了 UNVERIFIED），保证逐字还原。
渲染回导入时的语言，与原文件逐字相同；换一种语言时，表头、verified 列（有结构化结果时）按该语言生成，
研究者写的文字（表外内容、判定依据）不翻译。
check() 把 PROJECT.md 的硬规则变成可以机器检查的条目：取值合法、标识符来自检索结果（规则 b）、
题目 / 年份 / 作者与检索结果一致、判定依据里引号内的英文是摘要原文。
"""
import hashlib
import html
import re
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import defaults as D
from . import i18n
from .i18n import t
from .io import load_json_lenient, read_text
from .record import short_authors
from .verification import render_verified

SCHEMA = "novelty-probe/evidence@1"
_CELL_SPLIT = re.compile(r"(?<!\\)\|")
_DOI_IN_CELL = re.compile(r"doi:\s*(10\.\d{4,9}/[^\s·|]+)", re.I)
_ARXIV_IN_CELL = re.compile(r"arxiv:\s*([\w./-]+?\d)(?=\s|·|$)", re.I)
_BLOCK_RE = re.compile(r"^\*\*(\d+)(?:\s*·\s*([^*]+?))?\*\*(.*)$")
_QUOTE_RE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”')
_CJK_RE = re.compile(r"[　-〿一-鿿＀-￯]")
_TAG_RE = re.compile(r"<[^>]+>")
# 判定依据里注明的来源（另一个版本）：doi:… 或 arXiv:…（到空白或中英文标点为止）
_CITED_DOI_RE = re.compile(r"doi:\s*(10\.\d{4,9}/[^\s·|，,；;）)（(\]]+)", re.I)
_CITED_ARXIV_RE = re.compile(r"arxiv:\s*(\d{4}\.\d{4,5}|[a-z-]+/\d{7})", re.I)


class EvidenceError(ValueError):
    pass


# ---------- 小工具 ----------

def split_row(line):
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")) or len(s) < 2:
        return None
    return [c.strip() for c in _CELL_SPLIT.split(s[1:-1])]


def _unescape(cell):
    return cell.replace("\\|", "|")


def _escape(text):
    return str(text).replace("|", "\\|")


def _row_line(cells):
    return "| " + " | ".join(cells) + " |"


def norm_doi(doi):
    """比较用的 DOI：小写；去掉解析器前缀、URL 查询串与落地页后缀（与 scripts/textmatch.py 的 norm_doi 相同）。"""
    if not doi:
        return None
    d = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", doi.strip().lower())
    d = re.split(r"[?#]", d)[0]
    return re.sub(r"/(?:full|abstract|pdf|epdf|html)(?:/html)?/?$", "", d) or None


def identifiers(doi=None, arxiv_id=None, alt_ids=()):
    """一条记录的全部标识符：{("doi", …), ("arxiv", …)}；arXiv ID 同时记成 arXiv DOI。"""
    ids = set()
    if doi:
        ids.add(("doi", norm_doi(doi)))
    if arxiv_id:
        a = arxiv_id.strip().lower()
        ids |= {("arxiv", a), ("doi", f"10.48550/arxiv.{a}")}
    for alt in alt_ids or ():
        kind, _, val = alt.partition(":")
        if kind.lower() == "doi":
            ids.add(("doi", norm_doi(val)))
        elif val:
            ids |= {("arxiv", val.lower()), ("doi", f"10.48550/arxiv.{val.lower()}")}
    return ids


def _words(text):
    """比较用：去 HTML、去重音、小写，只留字母数字组成的词（标点与空白差异不计）。"""
    text = html.unescape(_TAG_RE.sub(" ", text or ""))
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.findall(r"[^\W_]+", text.lower())


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@contextmanager
def _language(lang):
    old = i18n.get_language()
    i18n.set_language(lang)
    try:
        yield
    finally:
        i18n.set_language(old)


def id_cell(doi, arxiv_id):
    parts = ([f"doi:{doi}"] if doi else []) + ([f"arXiv:{arxiv_id}"] if arxiv_id else [])
    return " · ".join(parts)


def default_columns(facets):
    return ([{"key": k, "header": None} for k in ("rank", "authors", "year", "title", "id")]
            + [{"key": f"facet:{f['key']}", "header": None} for f in facets] + [{"key": "verified", "header": None}])


def column_header(col, lang, facets):
    key = col["key"]
    if key.startswith("facet:"):
        f = next((f for f in facets if f["key"] == key[6:]), None)
        if f:
            return f["label"].get(lang) or next(iter(f["label"].values()))
        return key[6:]
    if key.startswith("extra:"):
        return key[6:]
    return D.COLUMN_HEADERS[key][lang]


def new_document(cfg, language=None):
    """空的证据文档（直接写 JSON 时从这里开始）。"""
    return {"schema": SCHEMA,
            "meta": {"language": language or cfg.get("language", "zh"), "facets": cfg["facets"], "labels": cfg["labels"],
                     "columns": default_columns(cfg["facets"]), "results": None, "markdown": None,
                     "imported_from": None, "updated_at": None, "rendered_sha256": None},
            "rows": []}


# ---------- 导入 Markdown ----------

def import_markdown(text, cfg, language=None, source=None):
    """Markdown 证据表 → 文档。找不到主表（含 DOI/arXiv 与 verified 列的表头）时抛 EvidenceError。"""
    columns_cfg, facets = cfg["columns"], cfg["facets"]
    lines = text.split("\n")
    final_newline = text.endswith("\n")
    if final_newline:
        lines = lines[:-1]
    header = None
    for i, line in enumerate(lines):
        cells = split_row(line)
        if cells and D.find_column(cells, "id", columns_cfg) is not None \
                and D.find_column(cells, "verified", columns_cfg) is not None:
            header = i
            break
    if header is None or header + 1 >= len(lines):
        raise EvidenceError(t("evidence.no_table", path=source or "<text>"))
    heads = split_row(lines[header])
    fcols = D.facet_columns(heads, facets)
    by_index = {}
    for key in ("rank", "authors", "year", "title", "id", "verified"):
        idx = D.find_column(heads, key, columns_cfg)
        if idx is not None:
            by_index[idx] = key
    for key, idx in fcols.items():
        by_index.setdefault(idx, f"facet:{key}")
    columns = [{"key": by_index.get(i, f"extra:{h}"), "header": h} for i, h in enumerate(heads)]
    end = header + 2
    rows = []
    while end < len(lines) and (cells := split_row(lines[end])) is not None:
        rows.append(_parse_row(cells, columns))
        end += 1
    after = lines[end:]
    middle, blocks, postamble = _split_rationale(after)
    by_rank, orphans = {}, []
    for rank, mid, note, block_lines in blocks:
        row = next((r for r in rows if str(r.get("rank")) == rank and "rationale" not in r), None)
        if row is None:
            orphans.append({"heading": f"**{rank}" + (f" · {mid}" if mid else "") + f"**{note}", "lines": block_lines})
            continue
        row["merged_id"] = mid
        row["rationale"] = {"note": note, "lines": block_lines}
        by_rank[rank] = row
    lang = language or _guess_language(heads, cfg)
    doc = {"schema": SCHEMA,
           "meta": {"language": lang, "facets": facets, "labels": cfg["labels"], "columns": columns, "results": None,
                    "markdown": None, "imported_from": source, "updated_at": _now(), "rendered_sha256": _sha256(text)},
           "sections": {"preamble": lines[:header], "separator": lines[header + 1], "middle": middle,
                        "postamble": postamble, "final_newline": final_newline},
           "rows": rows}
    if orphans:
        doc["orphan_rationale"] = orphans
    return doc


def _guess_language(heads, cfg):
    """表头用的是哪种语言的面标签 / 列名：有中文表头记 zh，否则 en。"""
    return "zh" if any(_CJK_RE.search(h) for h in heads) else ("en" if heads else cfg.get("language", "zh"))


def _parse_row(cells, columns):
    row = {"rank": None, "merged_id": None, "authors": None, "year": None, "title": None, "doi": None, "arxiv_id": None,
           "labels": {}, "verified_text": None, "cells_raw": {}, "extra": {}}
    for col, raw in zip(columns, cells + [""] * (len(columns) - len(cells))):
        key, val = col["key"], _unescape(raw)
        if key == "rank":
            row["rank"] = int(val) if val.isdigit() else val
        elif key == "year":
            row["year"] = int(val) if val.isdigit() else (val or None)
            if val and not val.isdigit():
                row["cells_raw"]["year"] = val
        elif key in ("authors", "title"):
            row[key] = val
        elif key == "id":
            doi, arx = _DOI_IN_CELL.search(val), _ARXIV_IN_CELL.search(val)
            row["doi"] = doi.group(1).rstrip(".,;") if doi else None
            row["arxiv_id"] = arx.group(1) if arx else None
            if id_cell(row["doi"], row["arxiv_id"]) != val:
                row["cells_raw"]["id"] = val
        elif key == "verified":
            row["verified_text"] = val
        elif key.startswith("facet:"):
            row["labels"][key[6:]] = val
        else:
            row["extra"][col["header"]] = val
    if len(cells) > len(columns):
        row["cells_raw"]["_overflow"] = cells[len(columns):]
    return row


def _split_rationale(after):
    """表后的行 → (middle, [(rank, merged_id, note, 行)], postamble)。判定依据块以 **N · Mxxx** 开头，
    到下一个块或下一个 "## " 标题为止；第一个块之前的行是 middle，块之后从 "## " 起是 postamble。"""
    first = next((i for i, l in enumerate(after) if _BLOCK_RE.match(l)), None)
    if first is None:
        return after, [], []
    middle, blocks, cur, i = after[:first], [], None, first
    while i < len(after):
        line = after[i]
        m = _BLOCK_RE.match(line)
        if m:
            cur = [m.group(1), (m.group(2) or "").strip() or None, m.group(3), []]
            blocks.append(cur)
        elif line.startswith("#"):
            break
        else:
            cur[3].append(line)
        i += 1
    return middle, [tuple(b) for b in blocks], after[i:]


# ---------- 渲染 Markdown ----------

def render_markdown(doc, lang=None):
    meta = doc["meta"]
    lang = lang or meta.get("language") or "zh"
    same = lang == meta.get("language")
    facets = meta.get("facets") or D.FACETS
    cols = meta.get("columns") or default_columns(facets)
    sec = doc.get("sections")
    out = []
    if sec:
        out += sec["preamble"]
    else:
        with _language(lang):
            out += [f"# {meta.get('title') or t('evidence.default_title')}", "", f"## {t('evidence.heading_table')}", ""]
    out.append(_row_line([c["header"] if same and c.get("header") else column_header(c, lang, facets) for c in cols]))
    out.append(sec["separator"] if sec and sec.get("separator") else "|" + "---|" * len(cols))
    with _language(lang):
        for row in doc["rows"]:
            out.append(_row_line([_escape(_cell(row, c)) for c in cols] + list(row.get("cells_raw", {}).get("_overflow", []))))
    if sec:
        out += sec["middle"]
    else:
        with _language(lang):
            out += ["", f"## {t('evidence.heading_rationale')}", ""]
    for row in doc["rows"]:
        r = row.get("rationale")
        if r is not None:
            out.append(f"**{row['rank']}" + (f" · {row['merged_id']}" if row.get("merged_id") else "") + f"**{r.get('note') or ''}")
            out += r.get("lines") or []
    for o in doc.get("orphan_rationale") or []:
        out.append(o["heading"])
        out += o["lines"]
    if sec:
        out += sec["postamble"]
    text = "\n".join(out)
    return text + "\n" if (sec or {}).get("final_newline", True) else text


def _cell(row, col):
    key, raw = col["key"], row.get("cells_raw") or {}
    if key in raw:
        return raw[key]
    if key == "rank":
        return "" if row.get("rank") is None else str(row["rank"])
    if key == "year":
        return "" if row.get("year") is None else str(row["year"])
    if key in ("authors", "title"):
        return row.get(key) or ""
    if key == "id":
        return id_cell(row.get("doi"), row.get("arxiv_id"))
    if key == "verified":
        if row.get("verification") is not None:
            return render_verified(row["verification"])
        return row.get("verified_text") or ""
    if key.startswith("facet:"):
        return (row.get("labels") or {}).get(key[6:], "")
    return (row.get("extra") or {}).get(key[6:], "")


# ---------- 读写 ----------

def load(path, cfg):
    """读证据文件：.json 直接读（检查 schema），.md 先导入。"""
    path = Path(path)
    if path.suffix.lower() == ".json":
        doc = load_json_lenient(path)
        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
            raise EvidenceError(t("evidence.bad_schema", path=path, schema=SCHEMA))
        return doc
    return import_markdown(read_text(path), cfg, source=str(path))


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def markdown_was_edited(doc, md_path):
    """Markdown 文件在上次导入或渲染之后被手工改过：返回 True（这时不应直接覆盖，应先重新导入）。"""
    md_path = Path(md_path)
    if not md_path.is_file():
        return False
    stored = (doc.get("meta") or {}).get("rendered_sha256")
    return stored is not None and stored != _sha256(read_text(md_path))


def mark_rendered(doc, text):
    doc["meta"]["rendered_sha256"] = _sha256(text)
    doc["meta"]["updated_at"] = _now()


def keep_structured_verification(doc, previous):
    """重新导入 Markdown 时，沿用旧 JSON 中同一 DOI 的结构化核验结果（verified 列只由 verify.py 写，Markdown 里的文字不作数）。"""
    old = {norm_doi(r.get("doi")): r["verification"] for r in (previous or {}).get("rows", [])
           if r.get("doi") and r.get("verification")}
    kept = 0
    for r in doc["rows"]:
        v = old.get(norm_doi(r.get("doi"))) if r.get("doi") else None
        if v:
            r["verification"] = v
            r.pop("verified_text", None)
            kept += 1
    return kept


# ---------- 种子（snowball.py --from-evidence） ----------

def seeds(doc, min_overlap, overlap="overlap"):
    """至少 min_overlap 个面标为 overlap 的行：[(标签, DOI, arXiv ID)]。"""
    out = []
    for r in doc["rows"]:
        n = sum(v == overlap for v in (r.get("labels") or {}).values())
        if n >= min_overlap:
            out.append((f"rank {r['rank']}", r.get("doi"), r.get("arxiv_id")))
    return out


# ---------- 检查 ----------

def quotes_in(line):
    """判定依据一行中引号内的英文片段（含中文的引号内容是转述，不检查）。引号个数为奇数时返回 None（无法可靠配对）。"""
    if line.count('"') % 2:
        return None
    out = []
    for m in _QUOTE_RE.finditer(line):
        q = m.group(1) or m.group(2)
        if not _CJK_RE.search(q) and len(re.findall(r"[A-Za-z]", q)) >= 3:
            out.append(q)
    return out


def quote_found(quote, abstracts):
    """引文按词序出现在某份摘要里（大小写、标点、空白差异不计；"..." / "…" 表示省略，各段分别查找、依次出现）。"""
    parts = [p for p in re.split(r"\.\.\.|…", quote) if _words(p)]
    for a in abstracts:
        hay = " " + " ".join(_words(a)) + " "
        pos = 0
        for p in parts:
            k = hay.find(" " + " ".join(_words(p)) + " ", pos)
            if k < 0:
                break
            pos = k + 1
        else:
            if parts:
                return True
    return False


class RetrievalIndex:
    """检索结果（合并结果 + enrich.py 补到的版本）中的标识符、题目、年份、摘要，供 check() 查询。"""

    def __init__(self, records=(), enrichment=(), authors=()):
        self.records = list(records)
        self.ids = set()
        self.by_id = {}
        for x in self.records:
            for k in identifiers(x.get("doi"), x.get("arxiv_id"), x.get("alt_ids")):
                self.ids.add(k)
                self.by_id.setdefault(k, x)
        self.extra_abstracts = {}    # 标识符 → [摘要]（来自 enrichment，注明来源 DOI 的其他版本）
        self.extra_ids = set()
        for e in enrichment:
            keys = set(e.get("_ids") or ())
            src = e.get("abstract_source") or {}
            for k in identifiers(src.get("doi"), e.get("arxiv_id_from_version")):
                keys.add(k)
                self.extra_ids.add(k)
            if e.get("doi_from_version"):
                k = ("doi", norm_doi(e["doi_from_version"]))
                keys.add(k)
                self.extra_ids.add(k)
            if e.get("abstract"):
                for k in keys:
                    self.extra_abstracts.setdefault(k, []).append(e["abstract"])
        # 作者：合并记录自带的（阶段 4 起检索时取得），以及 authors.py 的输出（同一篇两处都有时，与任一处一致即可）
        self.authors = {}
        for x in self.records:
            if x.get("authors"):
                for k in identifiers(x.get("doi"), x.get("arxiv_id"), x.get("alt_ids")):
                    self.authors.setdefault(k, []).append({"authors": x["authors"], "n_authors": x.get("n_authors")})
        for a in authors:
            if a.get("doi") and a.get("authors"):
                self.authors.setdefault(("doi", norm_doi(a["doi"])), []).append(a)

    def record_for(self, ids):
        return next((self.by_id[k] for k in sorted(ids) if k in self.by_id), None)

    def abstracts_for(self, ids, record=None):
        out = [record["abstract"]] if record and record.get("abstract") else []
        for k in sorted(ids):
            out += self.extra_abstracts.get(k, [])
        return out


def load_index(results=None, enrichment=(), authors=None):
    """读检索结果：results（merged*.json）、enrichment（enrich.py 的输出，可多个）、authors（authors.py 的输出）。"""
    records = load_json_lenient(results)["records"] if results else []
    extra = []
    for path in enrichment:
        data = load_json_lenient(path)
        cand = _candidate_ids(Path(path), data.get("meta") or {})
        for e in data.get("records") or []:
            extra.append({**e, "_ids": cand.get(e.get("merged_id"), set())})
    people = load_json_lenient(authors)["records"] if authors else []
    return RetrievalIndex(records, extra, people)


def _candidate_ids(path, meta):
    """enrichment 文件的 meta.input 指向它补充的候选表；按 merged_id 取候选的 DOI / arXiv ID。"""
    import csv
    inp = meta.get("input")
    if not inp:
        return {}
    root = path.resolve().parent.parent   # evidence/ 的上一级 = 项目根目录
    f = root / inp
    if not f.is_file():
        return {}
    with f.open(encoding="utf-8-sig", newline="") as fh:
        return {r["merged_id"]: identifiers(r.get("doi"), r.get("arxiv_id")) for r in csv.DictReader(fh)}


def cited_identifiers(lines):
    """判定依据中注明的标识符（如 "以下引文出自预印本 doi:10.48550/arxiv.2412.07727"）。"""
    ids = set()
    for line in lines or ():
        for m in _CITED_DOI_RE.finditer(line):
            ids |= identifiers(m.group(1).rstrip("."))
        for m in _CITED_ARXIV_RE.finditer(line):
            ids |= identifiers(None, m.group(1))
    return ids


def expected_authors(entry):
    """证据表的作者写法：前 3 位，作者总数超过 3 位时加 et al.（n_authors 缺省时按列表长度）。"""
    return short_authors([n for n in entry.get("authors") or [] if n], entry.get("n_authors"))


def check(doc, index=None):
    """返回 [(级别, 文字)]，级别为 error / warning。index 为 None 时只做不依赖检索结果的检查。"""
    meta = doc["meta"]
    facets = [f["key"] for f in meta.get("facets") or D.FACETS]
    labels = meta.get("labels") or D.LABELS
    present = [c["key"][6:] for c in meta.get("columns") or [] if c["key"].startswith("facet:")]
    out = []
    seen_rank, seen_ids = set(), {}
    for r in doc["rows"]:
        rank = r.get("rank")
        if rank in seen_rank:
            out.append(("error", t("evidence.duplicate_rank", rank=rank)))
        seen_rank.add(rank)
        for f in facets:
            if f not in present:
                continue
            v = (r.get("labels") or {}).get(f)
            if not v:
                out.append(("error", t("evidence.missing_facet", rank=rank, facet=f)))
            elif v not in labels:
                out.append(("error", t("evidence.bad_label", rank=rank, facet=f, value=v, labels="/".join(labels))))
        ids = identifiers(r.get("doi"), r.get("arxiv_id"))
        if not ids:
            out.append(("warning", t("evidence.no_identifier", rank=rank)))
            continue
        for k in ids:
            if k in seen_ids and seen_ids[k] != rank:
                out.append(("warning", t("evidence.duplicate_work", rank=rank, other=seen_ids[k])))
                break
        for k in ids:
            seen_ids.setdefault(k, rank)
        if index is None:
            continue
        own = [("doi", norm_doi(r["doi"]))] if r.get("doi") else []
        own += [("arxiv", r["arxiv_id"].lower())] if r.get("arxiv_id") else []
        for k in own:
            if k not in index.ids and k not in index.extra_ids:
                out.append(("error", t("evidence.id_not_retrieved", rank=rank, ident=f"{k[0]}:{k[1]}")))
        rec = index.record_for(ids)
        if rec is not None:
            if r.get("merged_id") and rec.get("merged_id") and r["merged_id"] != rec["merged_id"]:
                out.append(("warning", t("evidence.merged_id_mismatch", rank=rank, heading=r["merged_id"], record=rec["merged_id"])))
            if r.get("title") and _words(r["title"]) != _words(rec.get("title")):
                out.append(("error", t("evidence.title_mismatch", rank=rank, record=rec.get("title"))))
            if r.get("year") is not None and rec.get("year") is not None and str(r["year"]) != str(rec["year"]):
                out.append(("error", t("evidence.year_mismatch", rank=rank, value=r["year"], record=rec["year"])))
        options = [a for k in sorted(ids) for a in index.authors.get(k, ())]   # 同一篇的各个标识符（DOI、arXiv ID）下都算
        if options and r.get("authors") is not None and r["authors"] not in {expected_authors(a) for a in options}:
            out.append(("error", t("evidence.authors_mismatch", rank=rank, record=expected_authors(options[0]))))
        quotes, unbalanced = [], 0
        for line in (r.get("rationale") or {}).get("lines") or []:
            q = quotes_in(line)
            if q is None:
                unbalanced += 1
            else:
                quotes += q
        if unbalanced:
            out.append(("warning", t("evidence.unbalanced_quotes", rank=rank, n=unbalanced)))
        if not quotes:
            continue
        abstracts = index.abstracts_for(ids, rec)
        # 本篇没有摘要时，AGENTS.md 允许用同一研究其他版本的摘要并注明来源：判定依据里写明、且在检索结果中的记录也算
        cited = [index.by_id[k] for k in sorted(cited_identifiers((r.get("rationale") or {}).get("lines")) - ids)
                 if k in index.by_id]
        for k in sorted(cited_identifiers((r.get("rationale") or {}).get("lines")) - ids):
            abstracts += [a for a in index.extra_abstracts.get(k, []) if a not in abstracts]
        abstracts += [o["abstract"] for o in cited if o.get("abstract") and o["abstract"] not in abstracts]
        if not abstracts:
            out.append(("warning", t("evidence.no_abstract", rank=rank, n=len(quotes))))
            continue
        # 引号内也可以是检索记录的题目原文（如预印本题目后的 "(Just accepted by …)"）
        texts = abstracts + [x["title"] for x in [rec] + cited if x and x.get("title")]
        for q in quotes:
            if not quote_found(q, texts):
                out.append(("error", t("evidence.quote_not_found", rank=rank, quote=q[:80] + ("…" if len(q) > 80 else ""))))
    return out
