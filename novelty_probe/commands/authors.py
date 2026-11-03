#!/usr/bin/env python3
"""前几篇候选的作者，供 evidence/evidence_table.md 的"作者"列使用，写到 evidence/authors.json。

阶段 4 起 search.py 检索时就取得作者，合并结果（与候选表同目录的 merged{后缀}.json）里已有的直接取用，不再请求；
合并结果里没有作者的（如阶段 4 之前的检索结果），才按 DOI 查询 OpenAlex（GET /works/doi:<doi>），
同时记下 OpenAlex 返回的题目，便于核对查到的是同一篇。没有 DOI 又没有作者的条目不查询（authors 为 null）。
作者只取自检索结果或 API 返回，不补写。每条记录的 source 写明作者来自 search 还是 openalex。

用法：novelty-probe authors [--top 10]
      novelty-probe authors --candidates results/merged/candidates_v2.csv --out evidence/authors_v2.json
"""
import argparse
import csv
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from novelty_probe.paths import PACKAGE_ROOT
from novelty_probe import i18n, runtime
from novelty_probe.paths import rel as _rel
from novelty_probe.io import load_json_lenient, write_json

from novelty_probe.commands.search import get_json  # 复用检索命令的请求与重试逻辑（OpenAlex key 由环境注入）

ROOT = PACKAGE_ROOT   # 源码仓库（在仓库里运行时）；其他项目目录由 runtime.bind_root 换成该目录
CANDIDATES_FILE = ROOT / "results" / "merged" / "candidates.csv"
OUT_FILE = ROOT / "evidence" / "authors.json"


def rel(path):
    """项目内的路径显示为相对路径（正斜杠），项目外的显示为绝对路径。"""
    return _rel(path, ROOT)


def norm(t):
    return " ".join(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", t or "").lower()))


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Fetch authors from OpenAlex for the top candidates.")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--candidates", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    runtime.add_common_args(ap, network=True)
    args = ap.parse_args()
    rt = runtime.init(args)
    runtime.bind_root(globals(), rt.root, {"CANDIDATES_FILE": "results/merged/candidates.csv",
                                           "OUT_FILE": "evidence/authors.json"})
    client = rt.client
    cand_file, out_file = (args.candidates or CANDIDATES_FILE).resolve(), (args.out or OUT_FILE).resolve()
    with cand_file.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))[:args.top]
    merged_file = cand_file.with_name(cand_file.name.replace("candidates", "merged", 1)).with_suffix(".json")
    merged = {x["merged_id"]: x for x in load_json_lenient(merged_file)["records"]} if merged_file.is_file() else {}
    out, counts = [], {"from_search": 0, "looked_up": 0, "not_found": 0}
    for r in rows:
        rec = {"rank": int(r["rank"]), "merged_id": r["merged_id"], "doi": r["doi"] or None,
               "openalex_id": None, "openalex_title": None, "title_matches": None,
               "authors": None, "n_authors": None, "source": None, "error": None}
        x = merged.get(r["merged_id"]) or {}
        if x.get("authors"):                              # 检索时已取得（阶段 4 起）
            rec.update(authors=x["authors"], n_authors=x.get("n_authors"), source="search",
                       authors_from=(x.get("field_source") or {}).get("authors"))
            counts["from_search"] += 1
        elif not r["doi"]:
            rec["error"] = "no DOI; not queried"
        else:
            url = ("https://api.openalex.org/works/doi:" + urllib.parse.quote(r["doi"], safe="/")
                   + "?select=id,doi,display_name,authorships")
            try:
                w = get_json(url)
                names = [(a.get("author") or {}).get("display_name") or a.get("raw_author_name")
                         for a in (w.get("authorships") or [])]
                rec.update(openalex_id=w.get("id"), openalex_title=w.get("display_name"),
                           title_matches=norm(w.get("display_name")) == norm(r["title"]),
                           authors=names, n_authors=len(names), source="openalex")
                counts["looked_up"] += 1
            except RuntimeError as e:
                rec["error"] = str(e)
                counts["not_found"] += 1
        out.append(rec)
        first = rec["authors"][0] if rec["authors"] else "-"
        print(f"{rec['rank']:>3} {rec['merged_id']:<5} n_authors={rec['n_authors']!s:<4} "
              f"title_matches={rec['title_matches']!s:<5} first={first}  {rec['error'] or ''}")
    meta = {"source": "search results (merged records), else OpenAlex /works/doi:<doi>", "script": "scripts/authors.py",
            "input": rel(cand_file), "merged": rel(merged_file) if merged else None, "top": args.top, "counts": counts,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "http": client.stats_summary()}
    write_json(out_file, {"meta": meta, "records": out})
    print(f"authors from the search results: {counts['from_search']}; looked up in OpenAlex: {counts['looked_up']}")
    print(f"written: {rel(out_file)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
