#!/usr/bin/env python3
"""引文追踪（滚雪球）：从种子文献出发找有引用关系的文献，排序后输出，补关键词检索因措辞不同而漏掉的文献。

种子由研究者指定（--seeds），或取证据表中至少 N 个面标为 overlap 的文献（--from-evidence，默认 N=2）。
数据来自 OpenAlex（种子按 DOI 查；有 arXiv ID 时也查 arXiv DOI 10.48550/arXiv.<ID>，两条记录取并集）。

一步模式（默认，标签 C1）：
  后向  种子的 referenced_works；前向  GET /works?filter=cites:<种子>，按页取全（每个种子最多 --max-forward 条）。
  排序：与几篇种子有引用关系（links）→ 标题 + 摘要与种子的 TF-IDF 余弦相似度。
两步共被引（--cocite，标签 C2）：
  先取引用任一种子、且标题 + 摘要满足 --citer-filter 的文献（引用者；读者来信、回复、更正等不计），
  再统计这些引用者共同引用的文献：至少被 --min-support 篇（默认 2）引用的保留，
  按支持数 → 支持数 / √被引次数 排序（后者压低 PRISMA、VOSviewer 这类到处被引的通用文献）。
  引用者本身也列出（path=citer），按与种子的相似度排序。
  过滤词组由研究者决定；种子与想法只在"研究情境"面不同时，可用该面中"谁在用"的检索词。
  调研实测：v1 漏检的 Hao 等不在任何一步的结果中，在共被引中可以找到，但结果取决于过滤词组（见 docs/IMPROVEMENT_PLAN.md）。
query_blocks / conform 对照检索式文件给出满足的 AND 组比例与是否满足检索式，只作参考，不参与排序——追踪的目的
正是找出措辞与检索式不同的文献。
输出（不并入检索结果的排序）：
  results/raw/chase_<标签>{suffix}.json      排序后的前 --keep 条（默认 200；总数记在 meta.total_hits），格式与 search.py 相同，
                                             另加 chase 字段（路径、支持数、经由哪些引用者等）
  results/merged/chase_<标签>{suffix}.csv    每条路径各取前 --top 篇（默认 20），标出已在检索结果（merged{suffix}.json）中的
不判断相关性或新颖性；所有题目、DOI、摘要都取自 OpenAlex 的返回。

参数默认值来自配置 novelty-probe.json：snowball.min_overlap / max_forward / top / keep；证据表的面与列名取 facets / columns；
相似度的停用词取 textmatch.stopwords；截断词表取 queries.truncation（与 search.py 相同）。

用法：
  python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b
  python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b --cocite --citer-filter 'scientist*'
  python3 scripts/snowball.py --seeds 10.1126/sciadv.adn5290,arXiv:2402.01536 --suffix _v1b
"""
import argparse
import csv
import hashlib
import math
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe import config as np_config, defaults as D, evidence, i18n, runtime, schemas
from novelty_probe.http import Cursor, default_client
from novelty_probe.i18n import t
from novelty_probe.paths import rel as _rel
from novelty_probe.io import load_json_lenient, read_text, write_json

import search
from search import openalex_record
from novelty_probe.sources.openalex import CREDITS_PER_LIST_REQUEST
from textmatch import (Doc, centroid, content_terms, cosine, groups_matched, is_notice, query_match, tfidf_vectors,
                       title_key, version_title_match)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "results" / "raw"
OUT_DIR = ROOT / "results" / "merged"
OPENALEX_URL = "https://api.openalex.org/works"
FIELDS = ("id,doi,title,display_name,publication_year,type,primary_location,locations,abstract_inverted_index,"
          "cited_by_count")
_S = np_config.DEFAULTS["snowball"]   # 命令行参数的默认值（main() 里改用配置中的值）
MAX_FORWARD, TOP, KEEP = _S["max_forward"], _S["top"], _S["keep"]
BATCH = 50
OVERLAP = "overlap"   # 证据表中表示"重叠"的标注（配置 labels 中必须有它）
CSV_COLUMNS = ["path", "rank", "openalex_id", "links", "support", "norm_support", "seeds", "similarity",
               "query_blocks", "conform", "in_search", "doi", "arxiv_id", "title", "year", "venue", "cited_by_count",
               "abstract"]


def rel(path):
    """项目内的路径显示为相对路径（正斜杠），项目外的显示为绝对路径。"""
    return _rel(path, ROOT)


def oa_get(path_or_url, params=None, validate=None):
    """OpenAlex 请求，经统一客户端（限速、重试、缓存；key 由客户端加在请求头）。"""
    url = path_or_url if path_or_url.startswith("http") else OPENALEX_URL + path_or_url
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return default_client().get_json(url, validate=validate)


def oa_pages(flt, select, limit, label):
    """按 cursor 翻页取 OpenAlex 列表（每页 200 条，最多 limit 条）；断点写在 results/raw/.checkpoints/ 下，可续跑。
    第一页返回总数后，打印还要发多少个请求、约花多少 OpenAlex 额度。"""
    ck = RAW_DIR / ".checkpoints" / f"chase_{label}.json"
    per_page = min(200, max(1, limit))
    params = {"filter": flt, "select": select, "per-page": per_page}
    out, first = [], True
    fetch = lambda base, p: oa_get(base, p, validate=schemas.openalex_list)  # noqa: E731
    for page, items in default_client().paginate(OPENALEX_URL, params, scheme=Cursor(), max_items=limit, checkpoint=ck, fetch=fetch):
        if first and not page.get("_resumed"):
            count = (page.get("meta") or {}).get("count")
            if isinstance(count, int):
                n = min(count, limit)
                pages = max(1, math.ceil(n / per_page))
                print("  " + t("snowball.plan_pages", count=count, n=n, pages=pages, credits=pages * CREDITS_PER_LIST_REQUEST))
            first = False
        out.extend(items)
    return out[:limit]


def short_id(openalex_id):
    return (openalex_id or "").rsplit("/", 1)[-1]


# ---------- 种子 ----------

def seeds_from_evidence(path, min_overlap, facets=None, columns=None):
    """证据表（.md 或 .json）中至少 min_overlap 个面标为 overlap 的行：返回 [(标签, DOI, arXiv ID)]。
    Markdown 与 JSON 用同一个解析器（novelty_probe/evidence.py）；facets / columns 默认取内置定义，main() 传入配置中的定义。"""
    cfg = {"facets": facets or D.FACETS, "columns": columns or D.COLUMNS, "labels": D.LABELS}
    try:
        doc = evidence.load(path, cfg)
    except evidence.EvidenceError:
        sys.exit(t("snowball.no_header", path=path))
    return evidence.seeds(doc, min_overlap, overlap=OVERLAP)


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
            w = oa_get(f"/doi:{urllib.parse.quote(d, safe='/')}", {"select": FIELDS + ",referenced_works"})
            works.setdefault(w["id"], w)  # OpenAlex 已把两个版本并成一条时只算一次
        except RuntimeError as e:
            print(f"  seed lookup failed for {d}: {e}")
    return list(works.values())


# ---------- 追踪 ----------

def forward(work_ids, limit):
    """引用这些 OpenAlex 记录的文献（cursor 分页，可续跑）。"""
    return oa_pages("cites:" + "|".join(work_ids), FIELDS, limit, "forward_" + "_".join(work_ids)[:60])


def fetch_by_ids(ids):
    """按 OpenAlex ID 批量取元数据。ID 先排序再分批：请求确定，缓存与录制件才能命中。"""
    out = []
    ids = sorted(set(ids))
    if ids:
        batches = math.ceil(len(ids) / BATCH)
        print("  " + t("snowball.plan_ids", n=len(ids), batches=batches, credits=batches * CREDITS_PER_LIST_REQUEST))
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
    for r in load_json_lenient(path)["records"]:
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


def citing_works(seed_ids, expr, limit):
    """引用任一种子的文献；expr 为通用布尔式时只取标题 + 摘要满足它的（OpenAlex title_and_abstract.search）。
    返回 (记录列表, 不加过滤时的引用文献总数)。"""
    flt = "cites:" + "|".join(seed_ids)
    total = (oa_get("", {"filter": flt, "per-page": 1, "select": "id"}).get("meta") or {}).get("count")
    if expr:
        flt += ",title_and_abstract.search:" + search.to_openalex(expr)
    out = oa_pages(flt, FIELDS + ",referenced_works", limit, "citers_" + hashlib.sha1(flt.encode()).hexdigest()[:12])
    return out, total


def version_groups(works):
    """题目规范化后相同（≥5 词，且不是来信、更正之类的条目）的记录视为同一研究的不同版本：{work id: 组 id}。"""
    groups, by_key = {}, {}
    for w in works:
        wid, title = short_id(w["id"]), w.get("display_name") or w.get("title")
        k = title_key(title)
        groups[wid] = by_key.setdefault(k, wid) if len(k.split()) >= 5 and not is_notice(title) else wid
    return groups


def representative(ws):
    """同一研究的几个版本中选一条作代表：正式发表（非预印本 DOI）优先，其次有摘要、被引多。"""
    def score(w):
        doi = (w.get("doi") or "").lower()
        return (bool(doi) and "10.48550/arxiv" not in doi, bool(w.get("abstract_inverted_index")),
                w.get("cited_by_count") or 0)
    return max(ws, key=score)


def collect_onehop(args, seeds_resolved):
    links, pool = {}, {}  # links: work id -> {seed label: set(directions)}
    for label, works, info in seeds_resolved:
        ids = info["openalex_ids"]
        if args.direction in ("both", "backward"):
            for wid in {short_id(r) for w in works for r in w.get("referenced_works") or []}:
                links.setdefault(wid, {}).setdefault(label, set()).add("backward")
        if args.direction in ("both", "forward") and ids:
            citing = forward(ids, args.max_forward)
            info["citing_fetched"] = len(citing)
            for w in citing:
                pool[short_id(w["id"])] = w
                links.setdefault(short_id(w["id"]), {}).setdefault(label, set()).add("forward")
    seed_ids = {i for _, _, info in seeds_resolved for i in info["openalex_ids"]}
    for w in fetch_by_ids([wid for wid in links if wid not in pool and wid not in seed_ids]):
        pool[short_id(w["id"])] = w
    works = [w for wid, w in pool.items() if wid not in seed_ids]
    groups = version_groups(works)
    members = {}
    for w in works:
        members.setdefault(groups[short_id(w["id"])], []).append(w)
    rows = []
    for ws in members.values():  # 同一研究的几个版本合成一行，与种子的关系取并集
        lk = {}
        for w in ws:
            for label, dirs in links.get(short_id(w["id"]), {}).items():
                lk.setdefault(label, set()).update(dirs)
        rep = representative(ws)
        rows.append((rep, {"path": "onehop", "links": len(lk), "seeds": sorted(lk),
                           "directions": sorted({x for v in lk.values() for x in v}),
                           "versions": sorted(short_id(w["id"]) for w in ws if w is not rep)}))
    return rows, {"direction": args.direction, "max_forward_per_seed": args.max_forward,
                  "versions_merged": len(works) - len(members)}


def collect_cocite(args, seeds_resolved):
    """两步：引用种子且满足 --citer-filter 的文献（引用者），再统计它们共同引用的文献。
    同一研究的不同版本（如期刊版与 SSRN 版）算一篇引用者；被引文献的不同版本（如预印本与正式版）合并计数。"""
    seed_ids = sorted({i for _, _, info in seeds_resolved for i in info["openalex_ids"]})
    citing, total = citing_works(seed_ids, args.citer_filter, args.max_forward)
    notices = [w for w in citing if is_notice(w.get("display_name"))]  # 读者来信、回复、更正：只围绕某一篇写，不计
    citers = [w for w in citing if not is_notice(w.get("display_name"))]
    cgroups = version_groups(citers)
    citer_members, refs = {}, {}
    for w in citers:
        g = cgroups[short_id(w["id"])]
        citer_members.setdefault(g, []).append(w)
        refs.setdefault(g, set()).update(short_id(r) for r in w.get("referenced_works") or [])
    cited_by = {}  # 被引文献 id -> 引用它的引用者组
    for g, rs in refs.items():
        for rid in rs - set(seed_ids):
            cited_by.setdefault(rid, set()).add(g)
    # 取被引文献的元数据以便合并版本；被引文献太多时只取已达到门槛的
    wanted = [rid for rid, gs in cited_by.items() if len(cited_by) <= 3000 or len(gs) >= args.min_support]
    fetched = fetch_by_ids(wanted)
    vgroups = version_groups(fetched)
    ref_members = {}
    for w in fetched:
        ref_members.setdefault(vgroups[short_id(w["id"])], []).append(w)
    rows = []
    for ws in ref_members.values():
        gs = set().union(*(cited_by[short_id(w["id"])] for w in ws))
        if len(gs) < args.min_support:
            continue
        rep = representative(ws)
        n = len(gs)
        cites = max(w.get("cited_by_count") or 0 for w in ws)
        rows.append((rep, {"path": "cocited", "support": n, "via": sorted(gs),
                           "norm_support": round(n / math.sqrt(max(cites, 1)), 4),
                           "versions": sorted(short_id(w["id"]) for w in ws if w is not rep)}))
    for g, ws in citer_members.items():
        rep = representative(ws)
        r = refs[g]
        rows.append((rep, {"path": "citer", "versions": sorted(short_id(w["id"]) for w in ws if w is not rep),
                           "seeds": sorted(label for label, _, info in seeds_resolved if set(info["openalex_ids"]) & r)}))
    stats = {"citer_filter": args.citer_filter, "citer_filter_sent": search.to_openalex(args.citer_filter)
             if args.citer_filter else None, "citing_total_unfiltered": total, "citing_filtered": len(citing),
             "citing_notices_excluded": [w.get("display_name") for w in notices],
             "citers_used": len(citer_members), "citer_versions_merged": len(citers) - len(citer_members),
             "min_support": args.min_support, "references_counted": len(cited_by),
             "cocited_kept": sum(1 for _, c in rows if c["path"] == "cocited")}
    return rows, stats


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Citation chasing from seed papers via OpenAlex: one hop, or two-hop co-citation.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seeds", help=t("snowball.arg.seeds"))
    g.add_argument("--from-evidence", type=Path, help=t("snowball.arg.from_evidence"))
    ap.add_argument("--min-overlap", type=int, default=None, help=t("snowball.arg.min_overlap"))
    ap.add_argument("--queries", type=Path, default=None, help=t("snowball.arg.queries"))
    ap.add_argument("--suffix", default="", help=t("snowball.arg.suffix"))
    ap.add_argument("--cocite", action="store_true", help=t("snowball.arg.cocite"))
    ap.add_argument("--citer-filter", help=t("snowball.arg.citer_filter"))
    ap.add_argument("--min-support", type=int, default=2, help=t("snowball.arg.min_support"))
    ap.add_argument("--direction", choices=["both", "backward", "forward"], default="both", help=t("snowball.arg.direction"))
    ap.add_argument("--max-forward", type=int, default=None, help=t("snowball.arg.max_forward"))
    ap.add_argument("--label", help=t("snowball.arg.label"))
    ap.add_argument("--top", type=int, default=None, help=t("snowball.arg.top"))
    ap.add_argument("--keep", type=int, default=None, help=t("snowball.arg.keep"))
    runtime.add_common_args(ap, network=True)
    args = ap.parse_args()
    rt = runtime.init(args)
    layout = {"RAW_DIR": "results/raw", "OUT_DIR": "results/merged"}
    runtime.bind_root(globals(), rt.root, layout)
    runtime.bind_root(vars(search), rt.root, {"QUERIES_FILE": "queries/queries.json", **layout})
    cfg, client = rt.cfg, rt.client
    search.configure(cfg)
    for name in ("min_overlap", "max_forward", "top", "keep"):   # 命令行没给的取配置
        if getattr(args, name) is None:
            setattr(args, name, cfg["snowball"][name])
    args.queries = args.queries or search.QUERIES_FILE
    stopwords = frozenset(cfg["textmatch"]["stopwords"])
    label = args.label or ("C2" if args.cocite else "C1")
    if args.citer_filter:
        search.parse_query(args.citer_filter)  # 语法检查，写法与检索式相同

    seeds = (parse_seed_list(args.seeds) if args.seeds
             else seeds_from_evidence(args.from_evidence, args.min_overlap, cfg["facets"], cfg["columns"]))
    if not seeds:
        sys.exit(t("snowball.no_seeds"))
    parsed = [search.parse_query(q["query"]) for q in search.load_queries(args.queries)]

    print(f"seeds ({len(seeds)}):")
    seeds_resolved, seed_docs = [], []
    for slabel, doi, arxiv_id in seeds:
        works = resolve_seed(doi, arxiv_id)
        info = {"label": slabel, "doi": doi, "arxiv_id": arxiv_id, "openalex_ids": [short_id(w["id"]) for w in works],
                "titles": [w.get("display_name") for w in works],
                "referenced_works": len({r for w in works for r in w.get("referenced_works") or []}),
                "cited_by_count": [w.get("cited_by_count") for w in works]}
        if works:
            best = max(works, key=lambda w: len(w.get("abstract_inverted_index") or {}))
            r = openalex_record(best, "seed")
            seed_docs.append(Doc(r["title"], r["abstract"]))
        seeds_resolved.append((slabel, works, info))
        print(f"  {slabel}: {', '.join(info['openalex_ids']) or 'NOT FOUND'} | refs {info['referenced_works']} | "
              f"cited by {info['cited_by_count']} | {(info['titles'] or ['-'])[0]}")

    rows, stats = collect_cocite(args, seeds_resolved) if args.cocite else collect_onehop(args, seeds_resolved)

    seed_titles = [t for _, _, info in seeds_resolved for t in info["titles"] if t]
    records = []
    for w, chase in rows:
        r = openalex_record(w, label)
        if any(version_title_match(r["title"], t) for t in seed_titles):
            continue  # 种子的其他版本（如题目相同的预印本）
        records.append((r, {"openalex_id": short_id(w["id"]), "cited_by_count": w.get("cited_by_count"), **chase}))
    docs = [Doc(r["title"], r["abstract"]) for r, _ in records]
    vecs = tfidf_vectors([content_terms(d, stopwords) for d in seed_docs + docs])
    seed_centroid = centroid(vecs[:len(seed_docs)]) if seed_docs else {}
    search_file, index = search_index(args.suffix)
    out = []
    for (r, chase), d, v in zip(records, docs, vecs[len(seed_docs):]):
        chase["similarity"] = round(cosine(seed_centroid, v), 4)
        chase["query_blocks"] = round(max((groups_matched(inc, d) / len(inc) for inc, _ in parsed), default=0.0), 3)
        chase["conform"] = any(query_match(inc, d, exc) for inc, exc in parsed)
        out.append({**r, "chase": chase, "in_search": lookup(index, r) if index else ""})

    def key(x):
        c = x["chase"]
        if c["path"] == "cocited":
            return (0, -c["support"], -c["norm_support"], c["openalex_id"])
        if c["path"] == "citer":
            return (1, -c["similarity"], 0, c["openalex_id"])
        return (0, -c["links"], -c["similarity"], c["openalex_id"])
    out.sort(key=key)

    meta = {"source_api": "openalex", "query_id": label, "purpose": "chase",
            "conversion": "citation chasing (OpenAlex referenced_works and cites:)",
            "mode": "cocite" if args.cocite else "onehop", "query_original": None,
            "seeds": [info for _, _, info in seeds_resolved], **stats, "queries_file": rel(args.queries),
            "sort": ("cocited: support desc, support/sqrt(cited_by_count) desc; citers: similarity to seeds desc"
                     if args.cocite else "links desc, similarity to seeds desc"),
            "total_hits": len(out), "returned": min(len(out), args.keep),
            "parameters": {k: getattr(args, k) for k in ("min_overlap", "max_forward", "top", "keep", "min_support", "direction")},
            **np_config.meta(cfg, rel), "http": client.stats_summary(),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    raw_path = RAW_DIR / f"chase_{label}{args.suffix}.json"
    write_json(raw_path, {"meta": meta, "records": [{k: v for k, v in x.items() if k != "in_search"} for x in out[:args.keep]]})
    shown, per_path = [], {}
    for x in out:
        k = x["chase"]["path"]
        per_path[k] = per_path.get(k, 0) + 1
        if per_path[k] <= args.top:
            shown.append((per_path[k], x))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"chase_{label}{args.suffix}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        wr.writeheader()
        for rank, x in shown:
            c = x["chase"]
            wr.writerow({"path": c["path"], "rank": rank, "openalex_id": c["openalex_id"], "links": c.get("links", ""),
                         "support": c.get("support", ""), "norm_support": c.get("norm_support", ""),
                         "seeds": ";".join(c.get("seeds", [])), "similarity": c["similarity"],
                         "query_blocks": c["query_blocks"], "conform": "true" if c["conform"] else "false",
                         "in_search": x["in_search"], "doi": x["doi"] or "", "arxiv_id": x["arxiv_id"] or "",
                         "title": x["title"] or "", "year": x["year"] or "", "venue": x["venue"] or "",
                         "cited_by_count": c["cited_by_count"] if c["cited_by_count"] is not None else "",
                         "abstract": x["abstract"] or ""})

    if args.cocite:
        print(f"\nciting works: {stats['citing_total_unfiltered']} cite the seeds; {stats['citing_filtered']} pass the "
              f"filter {stats['citer_filter_sent']!r}; {len(stats['citing_notices_excluded'])} letters/replies excluded; "
              f"{stats['citers_used']} citers used (versions of one work counted once: "
              f"{stats['citer_versions_merged']} merged)")
        print(f"co-cited: {stats['references_counted']} works cited by the citers; "
              f"{stats['cocited_kept']} cited by at least {args.min_support}")
    else:
        print(f"\npool: {len(out)} works linked to the seeds ({sum(x['chase']['links'] > 1 for x in out)} "
              f"linked to more than one seed)")
    print(f"already in search results ({rel(search_file) if search_file else 'none'}): "
          f"{sum(bool(x['in_search']) for x in out)}")
    print(f"written: {rel(raw_path)}, {rel(csv_path)}")
    print(f"\n{'path':<8} {'rank':>4} {'score':>6} {'sim':>6} {'in_search':>9}  {'identifier':<40} title")
    for rank, x in shown:
        c = x["chase"]
        score = c.get("support", c.get("links", ""))
        ident = f"doi:{x['doi']}" if x["doi"] else (f"arXiv:{x['arxiv_id']}" if x["arxiv_id"] else "UNVERIFIED")
        print(f"{c['path']:<8} {rank:>4} {score!s:>6} {c['similarity']:>6.3f} {x['in_search'] or '-':>9}  "
              f"{ident[:40]:<40} {(x['title'] or '')[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
