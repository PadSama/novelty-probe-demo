#!/usr/bin/env python3
"""核验 evidence/evidence_table.md 中每条文献的 DOI，并把结果写回 verified 列。

每个 DOI 做两项检查，都从 https://doi.org/<doi> 出发并跟随跳转：
  1. Crossref 元数据：带 Accept: application/vnd.citationstyles.csl+json 请求，doi.org 把请求转给
     登记机构（Crossref DOI 转到 api.crossref.org），返回登记的题目、期刊、年份、作者。
     把登记题目与表中题目对照：表中题目的词有八成以上出现在登记题目里记"题目一致"。
     遇到 429 / 5xx 指数退避重试（服务端要求等待超过 60 秒则不重试）。
  2. 落地页：带 Accept: text/html 请求，记录最终的 HTTP 状态和返回页的 <title>。
verified 列写成 "Crossref <结果>；落地页 <结果>"，例如：
  Crossref HTTP 200 · 题目一致 · <登记题目>；落地页 HTTP 200 (www.example.org) · <页面标题>
请求失败时写明失败位置与原因：
  BLOCKED at <域名> (network policy, proxy 403)   本环境的网络策略不允许访问该域名
  ERROR at <域名>: <原因>                          超时、连接失败、返回内容不是 JSON 等
出版商返回的 4xx / 5xx（如反爬虫的 403）照实记录为 "HTTP 403 (...) · <页面标题>"。
没有 DOI 的行写 UNVERIFIED（只有 arXiv ID 的行按本规则也写 UNVERIFIED）。
每次运行都会覆盖 verified 列的旧值。终端输出两项检查的跳转链与 Crossref 登记的期刊、年份、作者，
便于记日志。

用法：python3 scripts/verify.py [--table evidence/evidence_table.md]
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

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = ROOT / "evidence" / "evidence_table.md"
DOI_RESOLVER = "https://doi.org/"
USER_AGENT = "novelty-probe/0.1 (DOI verification script)"
HTML_ACCEPT = "text/html,application/xhtml+xml"
CSL_ACCEPT = "application/vnd.citationstyles.csl+json"
TIMEOUT = 30
MAX_BYTES = 512 * 1024
PAUSE = 1.0
CROSSREF_RETRIES = 5
MAX_RETRY_WAIT = 60

DOI_RE = re.compile(r"10\.\d{4,9}/\S+")
CELL_SPLIT = re.compile(r"(?<!\\)\|")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


class RecordingRedirects(urllib.request.HTTPRedirectHandler):
    """照常跟随跳转，同时记下每一跳 (状态码, 目标地址)。"""

    def __init__(self):
        super().__init__()
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append((code, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(doi, accept, retries=0):
    """请求 doi.org 并跟随跳转。返回 status / final_url / chain / body / charset / ctype / error。"""
    url = DOI_RESOLVER + urllib.parse.quote(doi, safe="/")
    for attempt in range(retries + 1):
        rec = RecordingRedirects()
        opener = urllib.request.build_opener(rec)  # 仍会使用 HTTPS_PROXY 等环境代理设置
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        res = {"status": None, "final_url": url, "chain": rec.chain, "body": b"",
               "charset": None, "ctype": None, "error": None, "attempts": attempt + 1}
        try:
            with opener.open(req, timeout=TIMEOUT) as resp:
                res.update(status=resp.status, final_url=resp.geturl(), body=resp.read(MAX_BYTES),
                           charset=resp.headers.get_content_charset(), ctype=resp.headers.get_content_type())
            return res
        except urllib.error.HTTPError as e:  # 4xx / 5xx 也是核验结果
            ra = e.headers.get("Retry-After", "")
            ra = int(ra) if ra.isdigit() else 0
            if (e.code == 429 or e.code >= 500) and attempt < retries and ra <= MAX_RETRY_WAIT:
                time.sleep(max(2 ** (attempt + 1), ra))
                continue
            try:
                body = e.read(MAX_BYTES)
            except Exception:
                body = b""
            res.update(status=e.code, final_url=e.geturl() or url, body=body,
                       charset=e.headers.get_content_charset(), ctype=e.headers.get_content_type())
            return res
        except urllib.error.URLError as e:
            res.update(error=str(e.reason), final_url=rec.chain[-1][1] if rec.chain else url)
            return res
        except (TimeoutError, ConnectionResetError) as e:
            res.update(error=f"{type(e).__name__}: {e}", final_url=rec.chain[-1][1] if rec.chain else url)
            return res


def host(url):
    return urllib.parse.urlsplit(url or "").hostname or "?"


def hops(res):
    return " -> ".join(f"{code} {host(u)}" for code, u in res["chain"]) or "(no redirect)"


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
    if "Tunnel connection failed: 403" in res["error"]:
        return f"BLOCKED at {h} (network policy, proxy 403)"
    scheme = urllib.parse.urlsplit(res["final_url"] or "").scheme
    if scheme and scheme != "https":  # 如 doi.org 跳到 http:// 地址：本环境只经代理访问 HTTPS
        h = f"{scheme}://{h}"
    return f"ERROR at {h}: {res['error'][:80]}"


def check_crossref(doi, table_title):
    res = fetch(doi, CSL_ACCEPT, retries=CROSSREF_RETRIES)
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
    ap = argparse.ArgumentParser(description="Verify DOIs in the evidence table via doi.org and Crossref.")
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    args = ap.parse_args()
    lines = args.table.read_text(encoding="utf-8").splitlines()

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
            land_res, land_part = check_landing(doi)
            cells[i_ver] = f"{cr_part}；{land_part}".replace("|", "\\|")
            failed += not ok
            key_cr = cr_part.split(" · ")[1] if ok else cr_part.split(" (")[0]
            key_land = land_part.split(" (")[0]
            tally_cr[key_cr] = tally_cr.get(key_cr, 0) + 1
            tally_land[key_land] = tally_land.get(key_land, 0) + 1
            print(f"[{rank}] doi:{doi}")
            print(f"      crossref:  {hops(cr_res)}  (attempts: {cr_res['attempts']})  -> {cr_part}")
            if meta:
                year = ((meta.get("issued") or {}).get("date-parts") or [[None]])[0][0]
                authors = "; ".join(a.get("family") or a.get("literal") or "?" for a in (meta.get("author") or [])[:3])
                print(f"                 registered: {meta.get('container-title') or '-'} | {year} | "
                      f"{meta.get('type') or '-'} | authors: {authors or '-'}")
            print(f"      landing:   {hops(land_res)}  -> {land_part}")
            time.sleep(PAUSE)
        lines[i] = "| " + " | ".join(cells) + " |"
        i += 1

    args.table.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nsummary crossref: " + " | ".join(f"{k}: {v}" for k, v in sorted(tally_cr.items())))
    print("summary landing:  " + " | ".join(f"{k}: {v}" for k, v in sorted(tally_land.items())))
    print(f"written: verified column in {args.table}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
