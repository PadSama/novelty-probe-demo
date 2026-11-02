#!/usr/bin/env python3
"""按 DOI 从 OpenAlex 查询作者，供 evidence/evidence_table.md 的"作者"列使用。

search.py 保存的字段不含作者，所以这里按 DOI 逐条查询 OpenAlex（GET /works/doi:<doi>），
把作者列表写到 evidence/authors.json。没有 DOI 的条目不查询（authors 为 null）。
作者只取自 API 返回，不补写。同时记下 OpenAlex 返回的题目，便于核对查到的是同一篇。

用法：python3 scripts/authors.py [--top 10]
      python3 scripts/authors.py --candidates results/merged/candidates_v2.csv --out evidence/authors_v2.json
"""
import argparse
import csv
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe.paths import rel as _rel
from novelty_probe.io import configure_console, write_json

from search import get_json  # 复用 search.py 的请求与重试逻辑（OpenAlex key 由环境注入）

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_FILE = ROOT / "results" / "merged" / "candidates.csv"
OUT_FILE = ROOT / "evidence" / "authors.json"


def rel(path):
    """项目内的路径显示为相对路径（正斜杠），项目外的显示为绝对路径。"""
    return _rel(path, ROOT)


def norm(t):
    return " ".join(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", t or "").lower()))


def main():
    configure_console()
    ap = argparse.ArgumentParser(description="Fetch authors from OpenAlex for the top candidates.")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--candidates", type=Path, default=CANDIDATES_FILE)
    ap.add_argument("--out", type=Path, default=OUT_FILE)
    args = ap.parse_args()
    cand_file, out_file = args.candidates.resolve(), args.out.resolve()
    with cand_file.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))[:args.top]
    out = []
    for r in rows:
        rec = {"rank": int(r["rank"]), "merged_id": r["merged_id"], "doi": r["doi"] or None,
               "openalex_id": None, "openalex_title": None, "title_matches": None,
               "authors": None, "n_authors": None, "error": None}
        if not r["doi"]:
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
                           authors=names, n_authors=len(names))
            except RuntimeError as e:
                rec["error"] = str(e)
        out.append(rec)
        first = (rec["authors"] or ["-"])[0] if rec["authors"] else "-"
        print(f"{rec['rank']:>3} {rec['merged_id']:<5} n_authors={rec['n_authors']!s:<4} "
              f"title_matches={rec['title_matches']!s:<5} first={first}  {rec['error'] or ''}")
    meta = {"source": "OpenAlex /works/doi:<doi>", "script": "scripts/authors.py",
            "input": rel(cand_file), "top": args.top,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    write_json(out_file, {"meta": meta, "records": out})
    print(f"written: {rel(out_file)}")


if __name__ == "__main__":
    main()
