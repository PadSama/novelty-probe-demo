#!/usr/bin/env python3
"""核验 evidence/evidence_table.md 中每条文献的 DOI，并把结果写回 verified 列。

每个 DOI 做两项检查，都从 https://doi.org/<doi> 出发并跟随跳转：
  1. Crossref 元数据：带 Accept: application/vnd.citationstyles.csl+json 请求，doi.org 把请求转给
     登记机构（Crossref DOI 转到 api.crossref.org），返回登记的题目、期刊、年份、作者。
     把登记题目与表中题目对照：表中题目的词有八成以上出现在登记题目里记"题目一致"。
     遇到 429 / 5xx 指数退避重试（服务端要求等待超过 60 秒则不重试）。
  2. 落地页：带 Accept: text/html 请求，记录最终的 HTTP 状态和返回页的 <title>（--no-landing 时跳过）。
先查登记机构（api.crossref.org/works/<doi>/agency）：不是 Crossref 登记的 DOI（如 arXiv 等 DataCite 登记的）
直接记 "Crossref 无记录（DataCite 登记的 DOI）"，不再走 doi.org → data.crosscite.org 那一跳（本环境不可达）。
Crossref 一项失败时（上述情况，或 DOI 未在 Crossref 登记），再按 DOI 查 OpenAlex（api.openalex.org/works/doi:<doi>），
能查到即算元数据核验通过。所有请求经 novelty_probe/http.py 的统一客户端（限速、重试、缓存、录制回放；--http-mode 等参数）。
落地页一项从 https:// 跳到 http:// 时改用 https://（Emerald、IEEE 等的 DOI 登记的是 http:// 地址）。
verified 列写成 "Crossref <结果>；落地页 <结果>"，Crossref 失败时中间加一段 OpenAlex 的结果，例如：
  Crossref HTTP 200 · 题目一致 · <登记题目>；落地页 HTTP 200 (www.example.org) · <页面标题>
  Crossref BLOCKED at data.crosscite.org (network policy, proxy 403)；OpenAlex · 题目一致 · <题目>；落地页 …
请求失败时写明失败位置与原因：
  BLOCKED at <域名> (network policy, proxy 403)   本环境的网络策略不允许访问该域名
  ERROR at <域名>: <原因>                          超时、连接失败、返回内容不是 JSON 等
出版商返回的 4xx / 5xx（如反爬虫的 403）照实记录为 "HTTP 403 (...) · <页面标题>"。
没有 DOI 的行写 UNVERIFIED（只有 arXiv ID 的行按本规则也写 UNVERIFIED）。
每次运行都会覆盖 verified 列的旧值。终端输出两项检查的跳转链与 Crossref 登记的期刊、年份、作者，
便于记日志。

用法：python3 scripts/verify.py [--table evidence/evidence_table.md] [--no-landing]
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe import schemas
from novelty_probe.http import BlockedByPolicy, HttpError, add_http_args, configure_from_args, content_charset, default_client
from novelty_probe.io import configure_console, read_text, write_text

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = ROOT / "evidence" / "evidence_table.md"
DOI_RESOLVER = "https://doi.org/"
OPENALEX_WORKS = "https://api.openalex.org/works/doi:"
CROSSREF_AGENCY = "https://api.crossref.org/works/"   # + <doi>/agency
HTML_ACCEPT = "text/html,application/xhtml+xml"
CSL_ACCEPT = "application/vnd.citationstyles.csl+json"
MAX_BYTES = 512 * 1024   # 落地页正文最多读取的字节数（超时、重试、限速见 novelty_probe/http.py）

DOI_RE = re.compile(r"10\.\d{4,9}/\S+")
CELL_SPLIT = re.compile(r"(?<!\\)\|")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def fetch(doi, accept, retries=None):
    """经统一客户端请求 doi.org 并跟随跳转（https → http 的跳转改用 https）。
    返回 status / final_url / chain / upgraded / body / charset / ctype / error / attempts；4xx、5xx 作为结果返回。"""
    url = DOI_RESOLVER + urllib.parse.quote(doi, safe="/")
    res = {"status": None, "final_url": url, "chain": [], "upgraded": [], "body": b"",
           "charset": None, "ctype": None, "error": None, "attempts": 1}
    try:
        r = default_client().request(url, accept=accept, errors_as_result=True, max_hops=10)
    except BlockedByPolicy as e:
        res.update(error="BLOCKED", final_url=e.url or url, chain=list(e.chain), detail=str(e))
        return res
    except HttpError as e:
        res.update(error=str(e), final_url=e.url or url, chain=list(e.chain), attempts=e.attempts)
        return res
    res.update(status=r.status, final_url=r.final_url, chain=list(r.chain), upgraded=list(r.upgraded),
               body=r.body[:MAX_BYTES], charset=content_charset(r.headers),
               ctype=(r.headers.get("content-type") or "").split(";")[0].strip() or None, attempts=r.attempts)
    return res


def registration_agency(doi):
    """DOI 的登记机构（crossref / datacite / …），查 Crossref 的 /works/<doi>/agency；查不到返回 None。
    arXiv 等 DataCite 登记的 DOI 在 Crossref 没有记录，doi.org 的内容协商会把它们转到 data.crosscite.org（本环境不可达），
    先问一次登记机构可以直接改走 OpenAlex。"""
    try:
        d = default_client().get_json(CROSSREF_AGENCY + urllib.parse.quote(doi, safe="/") + "/agency",
                                      validate=schemas.crossref_agency)
    except HttpError:
        return None
    return ((d.get("message") or {}).get("agency") or {}).get("id")


def host(url):
    return urllib.parse.urlsplit(url or "").hostname or "?"


def hops(res):
    up = set(res.get("upgraded") or ())
    return " -> ".join(f"{code} {host(u)}" + (" (http→https)" if u in up else "")
                       for code, u in res["chain"]) or "(no redirect)"


def clean(text, limit=None):
    """去 HTML 标签与多余空白；给了 limit 就截短（只用于显示，比对题目时用完整文本）。"""
    text = " ".join(html.unescape(TAG_RE.sub(" ", text or "")).split())
    return (text[:limit] + "…") if limit and len(text) > limit else text


def page_title(body, charset):
    m = TITLE_RE.search(body.decode(charset or "utf-8", errors="replace"))
    if not m:
        return None
    return clean(m.group(1), 120) or None


def csl_title(meta):
    t = meta.get("title")
    if isinstance(t, list):
        t = t[0] if t else None
    return clean(t) or None


def title_matches(table_title, other):
    words = re.findall(r"\w+", TAG_RE.sub(" ", table_title or "").lower())
    if not words or not other:
        return None
    other_words = set(re.findall(r"\w+", other.lower()))
    return sum(w in other_words for w in words) / len(words) >= 0.8


def failure(res):
    h = host(res["final_url"])
    if res["error"] == "BLOCKED" or "Tunnel connection failed: 403" in res["error"]:
        return f"BLOCKED at {h} (network policy, proxy 403)"
    scheme = urllib.parse.urlsplit(res["final_url"] or "").scheme
    if scheme and scheme != "https":  # 如 doi.org 跳到 http:// 地址：本环境只经代理访问 HTTPS
        h = f"{scheme}://{h}"
    return f"ERROR at {h}: {res['error'][:80]}"


def check_crossref(doi, table_title):
    agency = registration_agency(doi)
    if agency and agency != "crossref":
        res = {"status": None, "final_url": DOI_RESOLVER + doi, "chain": [], "upgraded": [], "body": b"", "charset": None,
               "ctype": None, "error": None, "attempts": 0, "agency": agency}
        return res, None, f"Crossref 无记录（{agency.capitalize()} 登记的 DOI）", False
    res = fetch(doi, CSL_ACCEPT)
    meta = None
    if not res["error"] and res["status"] == 200:
        try:
            meta = json.loads(res["body"].decode("utf-8"))
        except ValueError:
            res["error"] = f"unexpected content ({res['ctype']})"
    if res["error"]:
        part, ok = "Crossref " + failure(res), False
    elif meta is None:
        part, ok = f"Crossref HTTP {res['status']} ({host(res['final_url'])})", False
    else:
        t = csl_title(meta)
        m = title_matches(table_title, t)  # 用完整题目比对
        flag = "题目一致" if m else ("题目不一致" if m is False else "题目缺失")
        part, ok = f"Crossref HTTP 200 · {flag} · {clean(t, 120) or '(no title)'}", True
    return res, meta, part, ok


def check_openalex(doi, table_title):
    """Crossref 核验失败时的备用核验：按 DOI 查 OpenAlex，比对题目。"""
    try:
        w = default_client().get_json(OPENALEX_WORKS + urllib.parse.quote(doi, safe="/") + "?select=id,display_name,type,publication_year",
                                      validate=schemas.openalex_work)
    except HttpError as e:
        if e.status:
            return None, f"OpenAlex HTTP {e.status}" + (" (未收录该 DOI)" if e.status == 404 else ""), False
        return None, f"OpenAlex ERROR: {str(e)[:80]}", False
    t = clean(w.get("display_name"))
    m = title_matches(table_title, t)
    flag = "题目一致" if m else ("题目不一致" if m is False else "题目缺失")
    return w, f"OpenAlex · {flag} · {clean(t, 120) or '(no title)'}", True


def check_landing(doi):
    res = fetch(doi, HTML_ACCEPT)
    if res["error"]:
        return res, "落地页 " + failure(res)
    title = page_title(res["body"], res["charset"]) if res["body"] else None
    return res, f"落地页 HTTP {res['status']} ({host(res['final_url'])}) · {title or '(no <title>)'}"


def split_row(line):
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    return [c.strip() for c in CELL_SPLIT.split(s[1:-1])]


def main():
    configure_console()
    ap = argparse.ArgumentParser(description="Verify DOIs in the evidence table via doi.org and Crossref.")
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--no-landing", action="store_true", help="不检查出版商落地页，只做元数据核验")
    add_http_args(ap)
    args = ap.parse_args()
    client = configure_from_args(args)
    lines = read_text(args.table).splitlines()

    header = next((i for i, l in enumerate(lines)
                   if (c := split_row(l)) and "verified" in c and "DOI/arXiv" in c), None)
    if header is None:
        sys.exit(f"{args.table} 中找不到含 DOI/arXiv 与 verified 列的表头")
    cols = split_row(lines[header])
    i_doi, i_ver = cols.index("DOI/arXiv"), cols.index("verified")
    i_rank = cols.index("rank") if "rank" in cols else None
    i_title = next((cols.index(c) for c in ("题目", "Title", "title") if c in cols), None)  # 中文或英文表头

    print(f"verify run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}  table={args.table}")
    tally_cr, tally_land, failed = {}, {}, 0
    i = header + 2  # 跳过表头下面的分隔行
    while i < len(lines) and (cells := split_row(lines[i])) is not None:
        rank = cells[i_rank] if i_rank is not None else str(i)
        table_title = cells[i_title] if i_title is not None else ""
        m = DOI_RE.search(cells[i_doi])
        if not m:
            cells[i_ver] = "UNVERIFIED"
            tally_cr["UNVERIFIED"] = tally_cr.get("UNVERIFIED", 0) + 1
            print(f"[{rank}] no DOI -> UNVERIFIED")
        else:
            doi = m.group(0).rstrip(".,;")
            cr_res, meta, cr_part, ok = check_crossref(doi, table_title)
            parts, oa_part = [cr_part], None
            key_cr = cr_part.split(" · ")[1] if ok else cr_part.split(" (")[0]
            if not ok:  # Crossref 不可用或未登记：改用 OpenAlex 核验
                _, oa_part, ok = check_openalex(doi, table_title)
                parts.append(oa_part)
                if ok:
                    key_cr = "OpenAlex " + oa_part.split(" · ")[1]
            if args.no_landing:
                land_res, land_part = None, "落地页 skipped"
            else:
                land_res, land_part = check_landing(doi)
            cells[i_ver] = "；".join(parts + [land_part]).replace("|", "\\|")
            failed += not ok
            key_land = land_part.split(" (")[0]
            tally_cr[key_cr] = tally_cr.get(key_cr, 0) + 1
            tally_land[key_land] = tally_land.get(key_land, 0) + 1
            print(f"[{rank}] doi:{doi}")
            print(f"      crossref:  {hops(cr_res)}  (attempts: {cr_res['attempts']})  -> {cr_part}")
            if cr_res.get("agency"):
                print(f"                 registration agency: {cr_res['agency']} (api.crossref.org/works/<doi>/agency)")
            if meta:
                year = ((meta.get("issued") or {}).get("date-parts") or [[None]])[0][0]
                authors = "; ".join(a.get("family") or a.get("literal") or "?" for a in (meta.get("author") or [])[:3])
                print(f"                 registered: {meta.get('container-title') or '-'} | {year} | "
                      f"{meta.get('type') or '-'} | authors: {authors or '-'}")
            if oa_part:
                print(f"      openalex:  -> {oa_part}")
            print(f"      landing:   {hops(land_res) if land_res else '(skipped)'}  -> {land_part}")
        lines[i] = "| " + " | ".join(cells) + " |"
        i += 1

    write_text(args.table, "\n".join(lines) + "\n")
    print("\nhttp: " + json.dumps(client.stats_summary(), ensure_ascii=False))
    print("summary crossref: " + " | ".join(f"{k}: {v}" for k, v in sorted(tally_cr.items())))
    print("summary landing:  " + " | ".join(f"{k}: {v}" for k, v in sorted(tally_land.items())))
    print(f"written: verified column in {args.table}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
