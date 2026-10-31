#!/usr/bin/env python3
"""核验 evidence/evidence_table.md 中每条文献的 DOI，并把结果写回 verified 列。

对每个 DOI 请求 https://doi.org/<doi> 并跟随跳转，记录最终的 HTTP 状态和返回页的 <title>，
写成 "HTTP <状态> (<最终域名>) · <页面标题>"。没有 DOI 的行写 UNVERIFIED
（只有 arXiv ID 的行按本规则也写 UNVERIFIED）。
请求失败时写明失败位置与原因：
  BLOCKED at <域名> (network policy, proxy 403)   本环境的网络策略不允许访问该域名
  ERROR at <域名>: <原因>                          超时、连接失败等
出版商返回的 4xx / 5xx（如反爬虫的 403）照实记录为 "HTTP 403 (...) · <页面标题>"。
每次运行都会覆盖 verified 列的旧值。终端输出完整跳转链，以及页面标题是否与表中题目一致
（表中题目的词有八成以上出现在页面标题里即视为一致），便于记日志。

用法：python3 scripts/verify.py [--table evidence/evidence_table.md]
"""
import argparse
import html
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
TIMEOUT = 30
MAX_BYTES = 512 * 1024
PAUSE = 1.0

DOI_RE = re.compile(r"10\.\d{4,9}/\S+")
CELL_SPLIT = re.compile(r"(?<!\\)\|")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


class RecordingRedirects(urllib.request.HTTPRedirectHandler):
    """照常跟随跳转，同时记下每一跳 (状态码, 目标地址)。"""

    def __init__(self):
        super().__init__()
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append((code, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def page_title(body, charset):
    m = TITLE_RE.search(body.decode(charset or "utf-8", errors="replace"))
    if not m:
        return None
    return " ".join(html.unescape(m.group(1)).split())[:150] or None


def fetch(doi):
    rec = RecordingRedirects()
    opener = urllib.request.build_opener(rec)  # 仍会使用 HTTPS_PROXY 等环境代理设置
    url = DOI_RESOLVER + urllib.parse.quote(doi, safe="/")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "text/html,application/xhtml+xml"})
    res = {"request_url": url, "status": None, "final_url": url, "title": None, "chain": rec.chain, "error": None}
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            res.update(status=resp.status, final_url=resp.geturl(),
                       title=page_title(resp.read(MAX_BYTES), resp.headers.get_content_charset()))
    except urllib.error.HTTPError as e:  # 出版商返回的 4xx / 5xx 也是核验结果
        res.update(status=e.code, final_url=e.geturl() or res["final_url"])
        try:
            res["title"] = page_title(e.read(MAX_BYTES), e.headers.get_content_charset())
        except Exception:
            pass
    except urllib.error.URLError as e:
        res.update(error=str(e.reason), final_url=rec.chain[-1][1] if rec.chain else url)
    except (TimeoutError, ConnectionResetError) as e:
        res.update(error=f"{type(e).__name__}: {e}", final_url=rec.chain[-1][1] if rec.chain else url)
    return res


def host(url):
    return urllib.parse.urlsplit(url or "").hostname or "?"


def verified_cell(res):
    h = host(res["final_url"])
    if res["error"]:
        if "Tunnel connection failed: 403" in res["error"]:
            return f"BLOCKED at {h} (network policy, proxy 403)"
        return f"ERROR at {h}: {res['error'][:80]}"
    title = (res["title"] or "(no <title>)").replace("|", "\\|")
    return f"HTTP {res['status']} ({h}) · {title}"


def title_matches(table_title, page):
    words = re.findall(r"\w+", (table_title or "").lower())
    if not words or not page:
        return None
    page_words = set(re.findall(r"\w+", page.lower()))
    return sum(w in page_words for w in words) / len(words) >= 0.8


def split_row(line):
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    return [c.strip() for c in CELL_SPLIT.split(s[1:-1])]


def main():
    ap = argparse.ArgumentParser(description="Verify DOIs in the evidence table via doi.org.")
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
    i_title = cols.index("题目") if "题目" in cols else None

    print(f"verify run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}  table={args.table}")
    tally, failed = {}, 0
    i = header + 2  # 跳过表头下面的分隔行
    while i < len(lines) and (cells := split_row(lines[i])) is not None:
        rank = cells[i_rank] if i_rank is not None else str(i)
        m = DOI_RE.search(cells[i_doi])
        if not m:
            cells[i_ver] = "UNVERIFIED"
            print(f"[{rank}] no DOI -> UNVERIFIED")
        else:
            doi = m.group(0).rstrip(".,;")
            res = fetch(doi)
            cells[i_ver] = verified_cell(res)
            hops = " -> ".join(f"{code} {host(u)}" for code, u in res["chain"]) or "(no redirect)"
            match = title_matches(cells[i_title], res["title"]) if i_title is not None else None
            print(f"[{rank}] doi:{doi}\n      redirects: {hops}\n      result:    {cells[i_ver]}"
                  + (f"\n      title matches table: {match}" if match is not None else ""))
            failed += bool(res["error"])
            time.sleep(PAUSE)
        key = cells[i_ver].split(" (")[0].split(":")[0] if cells[i_ver] != "UNVERIFIED" else "UNVERIFIED"
        tally[key] = tally.get(key, 0) + 1
        lines[i] = "| " + " | ".join(cells) + " |"
        i += 1

    args.table.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nsummary: " + " | ".join(f"{k}: {v}" for k, v in sorted(tally.items())))
    print(f"written: verified column in {args.table}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
