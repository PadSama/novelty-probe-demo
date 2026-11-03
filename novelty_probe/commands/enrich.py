#!/usr/bin/env python3
"""为候选文献补全元数据：从同一研究的其他版本（如预印本与正式发表版）补摘要和 arXiv ID。

很多期刊版本在 OpenAlex、Semantic Scholar 和 Crossref 中都没有摘要（出版商不开放），但同一研究的预印本常常有。
本脚本对 candidates.csv 的前 N 篇，用题目在 OpenAlex 中检索（title.search），找出"标题键"相同的其他版本：
标题键 = 去掉末尾版本说明括注（如 "(Just accepted by Nature...)"）、统一引号与大小写后的字母数字词，
要求至少 6 个词完全相同、出版年份相差不超过 3 年、至少有一位作者同姓，并排除 "Re:"、更正、回复、评论等独立条目。
任一方在 OpenAlex 中没有作者信息时不做作者核对，记 author_check=unknown，需人工核对。

找到后：
- 候选没有摘要、而某个版本有摘要时，记下该摘要及其来源（OpenAlex ID、DOI、类型、年份）；
- 候选没有 arXiv ID、而某个版本是 arXiv 预印本（DOI 为 10.48550/arXiv.*）时，记下该 arXiv ID；
- 候选没有 DOI 时，记下非预印本版本的 DOI 作为待核验的线索（doi_from_version），需由 verify.py 核验。
结果写到 evidence/enrichment{suffix}.json，不改动 results/ 下的文件。所有补充内容都来自检索结果，并注明来源。

用法：novelty-probe enrich [--top 20] [--candidates results/merged/candidates.csv] [--out evidence/enrichment.json]
"""
import argparse
import csv
import re
import sys
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from novelty_probe.paths import PACKAGE_ROOT
from novelty_probe import config as np_config, i18n, runtime
from novelty_probe.i18n import tr
from novelty_probe.paths import rel as _rel
from novelty_probe.io import write_json

from novelty_probe.commands.search import get_json, rebuild_abstract
from novelty_probe.text import title_search_words, version_title_match

ROOT = PACKAGE_ROOT   # 源码仓库（在仓库里运行时）；其他项目目录由 runtime.bind_root 换成该目录
CANDIDATES_FILE = ROOT / "results" / "merged" / "candidates.csv"
OUT_FILE = ROOT / "evidence" / "enrichment.json"
OPENALEX_URL = "https://api.openalex.org/works"
MAX_YEAR_GAP = np_config.DEFAULTS["versions"]["year_window"]   # 配置 versions.year_window（与 merge.py 的版本识别一致）
ARXIV_DOI_RE = re.compile(r"^(?:https?://doi\.org/)?10\.48550/arxiv\.(.+)$", re.I)
PREPRINT_TYPES = {"preprint", "posted-content"}


def rel(path):
    """项目内的路径显示为相对路径（正斜杠），项目外的显示为绝对路径。"""
    return _rel(path, ROOT)


def bare_doi(doi):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi or "", flags=re.I) or None


def surnames(work):
    """OpenAlex 记录中各作者的姓（取署名最后一个词，去掉重音并小写）。"""
    out = set()
    for a in work.get("authorships") or []:
        name = ((a.get("author") or {}).get("display_name") or a.get("raw_author_name") or "").strip()
        if name:
            last = unicodedata.normalize("NFKD", name.split()[-1]).encode("ascii", "ignore").decode() or name.split()[-1]
            out.add(last.lower().strip(".,"))
    return out


def own_record(own_doi, own_arxiv):
    """候选自身在 OpenAlex 中的记录（用于取作者）；查不到时返回 None。"""
    doi = own_doi or (f"10.48550/arxiv.{own_arxiv}" if own_arxiv else None)
    if not doi:
        return None
    try:
        return get_json(f"{OPENALEX_URL}/doi:{urllib.parse.quote(doi, safe='/')}?select=id,doi,authorships")
    except RuntimeError:
        return None


def find_versions(title, year, own_doi, own_arxiv=None):
    """在 OpenAlex 中按题目检索，返回同一研究的其他版本：标题键相同、年份相差不超过 MAX_YEAR_GAP，
    并且与候选至少有一位作者同姓（任一方没有作者信息时记 author_check=unknown，仍保留，供人工核对）。"""
    words = title_search_words(title)
    if len(words) < 5:
        return []
    params = {"filter": "title.search:" + " ".join(words), "per-page": 25,
              "select": "id,doi,display_name,publication_year,type,abstract_inverted_index,authorships"}
    data = get_json(f"{OPENALEX_URL}?{urllib.parse.urlencode(params)}")
    results = data.get("results") or []
    own_ids = {f"10.48550/arxiv.{own_arxiv}".lower()} if own_arxiv else set()
    if own_doi:
        own_ids.add(own_doi.lower())
    own = next((w for w in results if (bare_doi(w.get("doi")) or "").lower() in own_ids), None)
    if own is None:
        own = own_record(own_doi, own_arxiv)
    own_names = surnames(own) if own else set()
    out = []
    for w in results:
        doi = bare_doi(w.get("doi"))
        if (doi or "").lower() in own_ids or (own and w.get("id") == own.get("id")):
            continue  # 候选自身
        if not version_title_match(title, w.get("display_name")):
            continue
        y = w.get("publication_year")
        if year and y and abs(int(year) - int(y)) > MAX_YEAR_GAP:
            continue
        names = surnames(w)
        check = "unknown" if not (names and own_names) else ("shared" if names & own_names else "none")
        if check == "none":
            continue  # 同名的不同研究
        abstract = rebuild_abstract(w.get("abstract_inverted_index"))
        m = ARXIV_DOI_RE.match(doi or "")
        out.append({"openalex_id": w.get("id"), "doi": doi, "arxiv_id": m.group(1) if m else None,
                    "type": w.get("type"), "year": y, "title": w.get("display_name"), "author_check": check,
                    "abstract_chars": len(abstract or ""), "_abstract": abstract})
    return out


def main():
    global MAX_YEAR_GAP
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Enrich top candidates from other versions of the same work (OpenAlex).")
    ap.add_argument("--top", type=int, default=None,
                    help=tr("处理候选表的前多少篇（默认取配置 enrich.top）", "Number of top candidates to process (default: config enrich.top)"))
    ap.add_argument("--candidates", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    runtime.add_common_args(ap, network=True)
    args = ap.parse_args()
    rt = runtime.init(args)
    runtime.bind_root(globals(), rt.root, {"CANDIDATES_FILE": "results/merged/candidates.csv",
                                           "OUT_FILE": "evidence/enrichment.json"})
    cfg, client = rt.cfg, rt.client
    MAX_YEAR_GAP = cfg["versions"]["year_window"]
    args.top = cfg["enrich"]["top"] if args.top is None else args.top
    cand_file, out_file = (args.candidates or CANDIDATES_FILE).resolve(), (args.out or OUT_FILE).resolve()
    with cand_file.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))[:args.top]

    records, n_abs, n_arx, n_doi = [], 0, 0, 0
    for r in rows:
        needs = [k for k, v in (("abstract", r["abstract"]), ("arxiv_id", r["arxiv_id"]), ("doi", r["doi"])) if not v]
        rec = {"rank": int(r["rank"]), "merged_id": r["merged_id"], "title": r["title"], "needs": needs,
               "versions": [], "abstract": None, "abstract_source": None,
               "arxiv_id_from_version": None, "doi_from_version": None, "error": None}
        if needs:
            try:
                versions = find_versions(r["title"], r["year"], r["doi"], r["arxiv_id"])
            except RuntimeError as e:
                versions, rec["error"] = [], str(e)
            rec["versions"] = [{k: v for k, v in x.items() if k != "_abstract"} for x in versions]
            if "abstract" in needs:
                best = max((x for x in versions if x["_abstract"]),
                           key=lambda x: (x["author_check"] == "shared", len(x["_abstract"])), default=None)
                if best:
                    rec["abstract"] = best["_abstract"]
                    rec["abstract_source"] = {k: best[k] for k in ("openalex_id", "doi", "type", "year", "author_check")}
                    n_abs += 1
            if "arxiv_id" in needs:
                rec["arxiv_id_from_version"] = next((x["arxiv_id"] for x in versions if x["arxiv_id"]), None)
                n_arx += bool(rec["arxiv_id_from_version"])
            if "doi" in needs:
                rec["doi_from_version"] = next((x["doi"] for x in versions
                                                if x["doi"] and x["type"] not in PREPRINT_TYPES and not x["arxiv_id"]), None)
                n_doi += bool(rec["doi_from_version"])
        records.append(rec)
        found = [k for k, v in (("abstract", rec["abstract"]), ("arxiv_id", rec["arxiv_id_from_version"]),
                                ("doi", rec["doi_from_version"])) if v]
        print(f"{rec['rank']:>3} {rec['merged_id']:<5} needs={','.join(needs) or '-':<22} versions={len(rec['versions'])} "
              f"found={','.join(found) or '-'} {rec['error'] or ''}")

    meta = {"source": "OpenAlex title.search (other versions of the same work)", "script": "scripts/enrich.py",
            "input": rel(cand_file), "top": args.top, "max_year_gap": MAX_YEAR_GAP, **np_config.meta(cfg, rel),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "http": client.stats_summary(),
            "counts": {"candidates": len(records), "missing_abstract": sum("abstract" in r["needs"] for r in records),
                       "abstract_added": n_abs, "arxiv_id_added": n_arx, "doi_suggested": n_doi}}
    write_json(out_file, {"meta": meta, "records": records})
    c = meta["counts"]
    print(f"\nmissing abstracts: {c['missing_abstract']} → added from another version: {c['abstract_added']}; "
          f"arXiv IDs added: {c['arxiv_id_added']}; DOIs suggested (verify before use): {c['doi_suggested']}")
    print(f"written: {rel(out_file)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
