#!/usr/bin/env python3
"""引文追踪（滚雪球）：从种子文献出发，找出它们引用的文献（后向）和引用它们的文献（前向），排序后输出。

关键词检索只能找到用了同样措辞的文献；措辞不同但研究同一问题的文献，常常与相关文献有引用关系。
种子由研究者指定（--seeds），或取证据表中至少 N 个面标为 overlap 的文献（--from-evidence）。

数据来自 OpenAlex：
  种子          GET /works/doi:<DOI>（有 arXiv ID 时也查 arXiv DOI 10.48550/arXiv.<ID>，预印本与正式版的引用分别统计，取并集）
  后向          种子记录的 referenced_works，再按 OpenAlex ID 批量取元数据
  前向          GET /works?filter=cites:<种子的 OpenAlex ID>，按页取全（每个种子最多 --max-forward 条）
排序（只用于决定先看哪些）：
  links         与几篇种子有引用关系（引用或被引用），多者在前；
  similarity    标题 + 摘要与种子的 TF-IDF 余弦相似度（词干，去停用词），在 links 相同时决定先后；
  query_blocks  对照检索式文件：满足的 AND 组比例（各检索式中取最高），只作参考，不参与排序——
                追踪的目的正是找出措辞与检索式不同的文献。
输出：
  results/raw/openalex_C1{suffix}.json      追踪到的全部文献，记录格式与 search.py 相同，另加 chase 字段
  results/merged/chase{suffix}.csv          排序后的前 --top 篇（默认 20），标出已在检索结果（merged{suffix}.json）中的
不判断相关性或新颖性；所有题目、DOI、摘要都取自 OpenAlex 的返回。

用法：
  python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --min-overlap 2
  python3 scripts/snowball.py --seeds 10.1126/sciadv.adn5290,arXiv:2402.01536 --suffix _v1b
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import search
from search import get_json, openalex_record
from textmatch import (Doc, centroid, content_terms, cosine, groups_matched, query_match, tfidf_vectors,
                       title_key, version_title_match)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "results" / "raw"
OUT_DIR = ROOT / "results" / "merged"
OPENALEX_URL = "https://api.openalex.org/works"
FIELDS = "id,doi,title,display_name,publication_year,type,primary_location,locations,abstract_inverted_index"
MAX_FORWARD = 2000
TOP = 20
BATCH = 50
PAUSE = 0.15
FACETS = ["研究问题", "作用机制", "研究情境", "数据与方法", "预期发现"]
DOI_IN_CELL = re.compile(r"doi:(10\.\d{4,9}/[^\s·|]+)", re.I)
ARXIV_IN_CELL = re.compile(r"arxiv:\s*([\w./-]+?\d)(?=\s|·|$)", re.I)
CSV_COLUMNS = ["rank", "openalex_id", "links", "directions", "seeds", "similarity", "query_blocks", "conform",
               "in_search", "doi", "arxiv_id", "title", "year", "venue", "abstract"]


def rel(path):
    p = Path(path).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def headers():
    key = os.environ.get("OPENALEX_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def oa_get(path_or_url, params=None):
    url = path_or_url if path_or_url.startswith("http") else OPENALEX_URL + path_or_url
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = get_json(url, headers())
    time.sleep(PAUSE)
    return data


def short_id(openalex_id):
    return (openalex_id or "").rsplit("/", 1)[-1]


# ---------- 种子 ----------

def seeds_from_evidence(path, min_overlap):
    """证据表中至少 min_overlap 个面标为 overlap 的行：返回 [(标签, DOI, arXiv ID)]。"""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    split = lambda l: [c.strip() for c in re.split(r"(?<!\\)\|", l.strip()[1:-1])]  # noqa: E731
    h = next((i for i, l in enumerate(lines) if l.startswith("|") and "DOI/arXiv" in split(l)), None)
    if h is None:
        sys.exit(f"{path} 中找不到含 DOI/arXiv 列的表头")
    cols = split(lines[h])
    out = []
    for l in lines[h + 2:]:
        if not l.startswith("|"):
            break
        cells = split(l)
        n = sum(cells[cols.index(f)] == "overlap" for f in FACETS if f in cols)
        if n >= min_overlap:
            cell = cells[cols.index("DOI/arXiv")]
            doi, arx = DOI_IN_CELL.search(cell), ARXIV_IN_CELL.search(cell)
            label = f"rank {cells[cols.index('rank')]}" if "rank" in cols else cell
            out.append((label, doi.group(1) if doi else None, arx.group(1) if arx else None))
    return out


def parse_seed_list(text):
    out = []
    for item in filter(None, (x.strip() for x in text.split(","))):
        if item.lower().startswith("arxiv:"):
            out.append((item, None, item.split(":", 1)[1]))
        else:
            out.append((item, re.sub(r"^(doi:|https?://(dx\.)?doi\.org/)", "", item, flags=re.I), None))
    return out


def resolve_seed(doi, arxiv_id):
    """种子在 OpenAlex 中的记录（正式版与 arXiv 版可能是两条）。"""
    works = {}
    for d in filter(None, [doi, f"10.48550/arXiv.{arxiv_id}" if arxiv_id else None]):
        try:
            w = oa_get(f"/doi:{urllib.parse.quote(d, safe='/')}", {"select": FIELDS + ",referenced_works,cited_by_count"})
            works.setdefault(w["id"], w)  # OpenAlex 已把两个版本并成一条时只算一次
        except RuntimeError as e:
            print(f"  seed lookup failed for {d}: {e}")
    return list(works.values())


# ---------- 追踪 ----------

def forward(work_ids, limit):
    """引用这些 OpenAlex 记录的文献（cursor 分页）。"""
    out, cursor = [], "*"
    while cursor and len(out) < limit:
        data = oa_get("", {"filter": "cites:" + "|".join(work_ids), "select": FIELDS,
                           "per-page": 200, "cursor": cursor})
        out.extend(data.get("results") or [])
        cursor = (data.get("meta") or {}).get("next_cursor")
    return out[:limit]


def fetch_by_ids(ids):
    out = []
    ids = list(ids)
    for i in range(0, len(ids), BATCH):
        chunk = [short_id(x) for x in ids[i:i + BATCH]]
        data = oa_get("", {"filter": "openalex_id:" + "|".join(chunk), "select": FIELDS, "per-page": BATCH})
        out.extend(data.get("results") or [])
    return out


def search_index(suffix):
    """merged{suffix}.json 中的检索结果：按 DOI、arXiv ID、标题键查 merged_id。"""
    path = OUT_DIR / f"merged{suffix}.json"
    if not path.exists():
        return None, {}
    index = {}
    for r in json.loads(path.read_text(encoding="utf-8"))["records"]:
        keys = [("doi", r["doi"].lower())] if r["doi"] else []
        keys += [("doi", a[4:].lower()) for a in r.get("alt_ids") or [] if a.startswith("doi:")]
        keys += [("arxiv", a.lower()) for a in [r["arxiv_id"]] + [x[6:] for x in r.get("alt_ids") or []
                                                              if x.startswith("arxiv:")] if a]
        if r["title"] and len(title_key(r["title"]).split()) >= 6:
            keys.append(("title", title_key(r["title"])))
        for k in keys:
            index.setdefault(k, r["merged_id"])
    return path, index


def lookup(index, rec):
    keys = []
    if rec["doi"]:
        keys.append(("doi", rec["doi"].lower()))
    if rec["arxiv_id"]:
        keys += [("arxiv", rec["arxiv_id"].lower()), ("doi", f"10.48550/arxiv.{rec['arxiv_id']}".lower())]
    if rec["title"] and len(title_key(rec["title"]).split()) >= 6:
        keys.append(("title", title_key(rec["title"])))
    return next((index[k] for k in keys if k in index), "")


def main():
    ap = argparse.ArgumentParser(description="Citation chasing (backward and forward) from seed papers via OpenAlex.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seeds", help="逗号分隔的 DOI 或 arXiv:<ID>")
    g.add_argument("--from-evidence", type=Path, help="证据表路径：取至少 --min-overlap 个面为 overlap 的行作种子")
    ap.add_argument("--min-overlap", type=int, default=2)
    ap.add_argument("--queries", type=Path, default=search.QUERIES_FILE, help="用于计算 query_blocks 的检索式文件")
    ap.add_argument("--suffix", default="", help="输出文件后缀，与对应检索结果一致，如 _v2")
    ap.add_argument("--direction", choices=["both", "backward", "forward"], default="both")
    ap.add_argument("--max-forward", type=int, default=MAX_FORWARD, help="每个种子最多取多少条前向引用")
    ap.add_argument("--top", type=int, default=TOP)
    args = ap.parse_args()

    seeds = parse_seed_list(args.seeds) if args.seeds else seeds_from_evidence(args.from_evidence, args.min_overlap)
    if not seeds:
        sys.exit("没有种子文献")
    queries = search.load_queries(args.queries)
    parsed = [search.parse_query(q["query"]) for q in queries]

    print(f"seeds ({len(seeds)}):")
    seed_info, links = [], {}          # links: work id -> {seed label: set(directions)}
    pool, seed_ids, seed_docs = {}, set(), []
    for label, doi, arxiv_id in seeds:
        works = resolve_seed(doi, arxiv_id)
        ids = [short_id(w["id"]) for w in works]
        seed_ids.update(ids)
        refs = {short_id(r) for w in works for r in w.get("referenced_works") or []}
        info = {"label": label, "doi": doi, "arxiv_id": arxiv_id, "openalex_ids": ids,
                "titles": [w.get("display_name") for w in works], "referenced_works": len(refs),
                "cited_by_count": [w.get("cited_by_count") for w in works]}
        if works:
            best = max(works, key=lambda w: len(w.get("abstract_inverted_index") or {}))
            r = openalex_record(best, "seed")
            seed_docs.append(Doc(r["title"], r["abstract"]))
        if args.direction in ("both", "backward"):
            for wid in refs:
                links.setdefault(wid, {}).setdefault(label, set()).add("backward")
        if args.direction in ("both", "forward") and ids:
            citing = forward(ids, args.max_forward)
            info["citing_fetched"] = len(citing)
            for w in citing:
                wid = short_id(w["id"])
                pool[wid] = w
                links.setdefault(wid, {}).setdefault(label, set()).add("forward")
        seed_info.append(info)
        print(f"  {label}: {', '.join(ids) or 'NOT FOUND'} | refs {len(refs)} | citing fetched {info.get('citing_fetched', 0)}"
              f" | {(info['titles'] or ['-'])[0]}")

    missing = [wid for wid in links if wid not in pool and wid not in seed_ids]
    for w in fetch_by_ids(missing):
        pool[short_id(w["id"])] = w
    for wid in seed_ids:
        links.pop(wid, None)
        pool.pop(wid, None)

    # 去掉种子的其他版本（如题目相同的预印本）
    seed_titles = [t for s in seed_info for t in s["titles"] if t]
    records = []
    for wid, w in pool.items():
        r = openalex_record(w, "C1")
        if any(version_title_match(r["title"], t) for t in seed_titles):
            continue
        records.append((wid, r))

    docs = [Doc(r["title"], r["abstract"]) for _, r in records]
    vecs = tfidf_vectors([content_terms(d) for d in seed_docs + docs])
    seed_centroid = centroid(vecs[:len(seed_docs)]) if seed_docs else {}
    sims = [cosine(seed_centroid, v) for v in vecs[len(seed_docs):]]
    search_file, index = search_index(args.suffix)

    rows = []
    for (wid, r), d, sim in zip(records, docs, sims):
        lk = links.get(wid, {})
        blocks = max((groups_matched(inc, d) / len(inc) for inc, _ in parsed), default=0.0)
        conform = any(query_match(inc, d, exc) for inc, exc in parsed)
        chase = {"openalex_id": wid, "links": len(lk), "seeds": sorted(lk),
                 "directions": sorted({x for v in lk.values() for x in v}),
                 "similarity": round(sim, 4), "query_blocks": round(blocks, 3), "conform": conform}
        rows.append({**r, "chase": chase, "in_search": lookup(index, r) if index else ""})
    rows.sort(key=lambda x: (-x["chase"]["links"], -x["chase"]["similarity"], x["chase"]["openalex_id"]))

    meta = {"source_api": "openalex", "query_id": "C1", "purpose": "chase",
            "conversion": "citation chasing (OpenAlex referenced_works and cites:)", "query_original": None,
            "direction": args.direction, "max_forward_per_seed": args.max_forward, "seeds": seed_info,
            "queries_file": rel(args.queries), "sort": "links desc, similarity desc",
            "total_hits": len(rows), "returned": len(rows),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"openalex_C1{args.suffix}.json"
    raw_path.write_text(json.dumps({"meta": meta, "records": [{k: v for k, v in x.items() if k != "in_search"}
                                                               for x in rows]}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"chase{args.suffix}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        wr.writeheader()
        for rank, x in enumerate(rows[:args.top], 1):
            c = x["chase"]
            wr.writerow({"rank": rank, "openalex_id": c["openalex_id"], "links": c["links"],
                         "directions": ";".join(c["directions"]), "seeds": ";".join(c["seeds"]),
                         "similarity": c["similarity"], "query_blocks": c["query_blocks"],
                         "conform": "true" if c["conform"] else "false", "in_search": x["in_search"],
                         "doi": x["doi"] or "", "arxiv_id": x["arxiv_id"] or "", "title": x["title"] or "",
                         "year": x["year"] or "", "venue": x["venue"] or "", "abstract": x["abstract"] or ""})

    multi = sum(x["chase"]["links"] > 1 for x in rows)
    print(f"\npool: {len(rows)} works linked to the seeds ({multi} linked to more than one seed); "
          f"already in search results ({rel(search_file) if search_file else 'none'}): "
          f"{sum(bool(x['in_search']) for x in rows)}")
    print(f"written: {rel(raw_path)}, {rel(csv_path)} (top {min(args.top, len(rows))})")
    print(f"\n{'rank':>4} {'links':>5} {'sim':>6} {'blocks':>6} {'in_search':>9}  {'identifier':<40} title")
    for rank, x in enumerate(rows[:args.top], 1):
        c = x["chase"]
        ident = f"doi:{x['doi']}" if x["doi"] else (f"arXiv:{x['arxiv_id']}" if x["arxiv_id"] else "UNVERIFIED")
        print(f"{rank:>4} {c['links']:>5} {c['similarity']:>6.3f} {c['query_blocks']:>6.2f} {x['in_search'] or '-':>9}  "
              f"{ident[:40]:<40} {(x['title'] or '')[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
