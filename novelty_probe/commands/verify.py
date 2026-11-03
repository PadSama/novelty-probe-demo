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
结构：check_crossref / check_openalex / check_landing 返回结构化结果（verify_doi 汇总），render_*() 按界面语言（--lang）
生成上面的文字；中文与改造前逐字相同。列名按配置 columns 识别；配置 verify.landing 为 false 时等同 --no-landing。

--table 是证据 JSON（evidence.py import-md 的输出）时，结构化结果写进 rows[].verification，再按 JSON 重新生成
meta.markdown 指向的 Markdown（该文件在上次导入或渲染后被手工改过时不覆盖，提示先重新导入）。

用法：novelty-probe verify [--table evidence/evidence_table.md|.json] [--no-landing] [--lang en]
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

from novelty_probe.paths import PACKAGE_ROOT
from novelty_probe import evidence, i18n, runtime, schemas
from novelty_probe.defaults import find_column
from novelty_probe.http import BlockedByPolicy, HttpError, content_charset, default_client
from novelty_probe.i18n import t
from novelty_probe.io import read_text, write_json, write_text
# 结构化结果 → verified 列文字（中文与改造前逐字相同）；放在包里，供 novelty_probe/evidence.py 渲染证据表时共用
from novelty_probe.verification import (clean, render_crossref, render_failure, render_landing,  # noqa: F401
                                        render_openalex, render_verified, tally_keys)

ROOT = PACKAGE_ROOT   # 源码仓库（在仓库里运行时）；其他项目目录由 runtime.bind_root 换成该目录
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


def failure_info(res):
    """请求失败的位置与原因（结构化）：kind = blocked（网络策略）/ error（超时、连接失败、内容不是 JSON 等）。"""
    h = host(res["final_url"])
    if res["error"] == "BLOCKED" or "Tunnel connection failed: 403" in res["error"]:
        return {"kind": "blocked", "host": h}
    scheme = urllib.parse.urlsplit(res["final_url"] or "").scheme
    if scheme and scheme != "https":  # 如 doi.org 跳到 http:// 地址：本环境只经代理访问 HTTPS
        h = f"{scheme}://{h}"
    return {"kind": "error", "host": h, "error": res["error"]}


def failure(res):
    return render_failure(failure_info(res))


# ---------- 三项检查：返回结构化结果（写进证据 JSON），展示文字由 render_*() 按界面语言生成 ----------

def check_crossref(doi, table_title):
    """→ (结果, HTTP 结果, CSL 元数据)。结果的 outcome：
    not_registered（不是 Crossref 登记的 DOI，agency 记登记机构）/ failed（failure）/ http（非 200）/ found（title、title_match）。"""
    agency = registration_agency(doi)
    if agency and agency != "crossref":
        res = {"status": None, "final_url": DOI_RESOLVER + doi, "chain": [], "upgraded": [], "body": b"", "charset": None,
               "ctype": None, "error": None, "attempts": 0, "agency": agency}
        return {"outcome": "not_registered", "agency": agency}, res, None
    res = fetch(doi, CSL_ACCEPT)
    meta = None
    if not res["error"] and res["status"] == 200:
        try:
            meta = json.loads(res["body"].decode("utf-8"))
        except ValueError:
            res["error"] = f"unexpected content ({res['ctype']})"
    if res["error"]:
        return {"outcome": "failed", "failure": failure_info(res)}, res, None
    if meta is None:
        return {"outcome": "http", "http": res["status"], "host": host(res["final_url"])}, res, None
    t_ = csl_title(meta)
    return {"outcome": "found", "http": 200, "title": t_, "title_match": title_matches(table_title, t_)}, res, meta  # 用完整题目比对


def check_openalex(doi, table_title):
    """Crossref 核验失败时的备用核验：按 DOI 查 OpenAlex，比对题目。outcome：http（如 404 未收录）/ failed / found。"""
    try:
        w = default_client().get_json(OPENALEX_WORKS + urllib.parse.quote(doi, safe="/") + "?select=id,display_name,type,publication_year",
                                      validate=schemas.openalex_work)
    except HttpError as e:
        if e.status:
            return {"outcome": "http", "http": e.status}
        return {"outcome": "failed", "error": str(e)}
    t_ = clean(w.get("display_name"))
    return {"outcome": "found", "title": t_, "title_match": title_matches(table_title, t_)}


def check_landing(doi):
    """→ (结果, HTTP 结果)。outcome：failed / http（http、host、page_title）。"""
    res = fetch(doi, HTML_ACCEPT)
    if res["error"]:
        return {"outcome": "failed", "failure": failure_info(res)}, res
    title = page_title(res["body"], res["charset"]) if res["body"] else None
    return {"outcome": "http", "http": res["status"], "host": host(res["final_url"]), "page_title": title}, res


def verify_doi(doi, table_title, landing=True):
    """一个 DOI 的完整核验：Crossref → （失败时）OpenAlex → 落地页。返回 (结构化结果, 供终端打印的细节)。"""
    cr, cr_res, meta = check_crossref(doi, table_title)
    result = {"doi": doi, "crossref": cr, "openalex": None, "landing": {"outcome": "skipped"}}
    ok = cr["outcome"] == "found"
    if not ok:  # Crossref 不可用或未登记：改用 OpenAlex 核验
        result["openalex"] = check_openalex(doi, table_title)
        ok = result["openalex"]["outcome"] == "found"
    land_res = None
    if landing:
        result["landing"], land_res = check_landing(doi)
    result["metadata_ok"] = ok
    return result, {"crossref_res": cr_res, "meta": meta, "landing_res": land_res}


def split_row(line):
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    return [c.strip() for c in CELL_SPLIT.split(s[1:-1])]


class Tally:
    def __init__(self):
        self.cr, self.land, self.failed = {}, {}, 0

    def add(self, v):
        if not v.get("doi"):
            self.cr["UNVERIFIED"] = self.cr.get("UNVERIFIED", 0) + 1
            return
        key_cr, key_land = tally_keys(v)
        self.cr[key_cr] = self.cr.get(key_cr, 0) + 1
        self.land[key_land] = self.land.get(key_land, 0) + 1
        self.failed += not v["metadata_ok"]


def verify_and_print(rank, id_text, table_title, landing):
    """核验一行（id_text 中找不到 DOI 时为 UNVERIFIED），打印细节，返回结构化结果。"""
    m = DOI_RE.search(id_text or "")
    if not m:
        print(f"[{rank}] no DOI -> UNVERIFIED")
        return {"doi": None}
    doi = m.group(0).rstrip(".,;")
    v, detail = verify_doi(doi, table_title, landing)
    cr_res, meta, land_res = detail["crossref_res"], detail["meta"], detail["landing_res"]
    print(f"[{rank}] doi:{doi}")
    print(f"      crossref:  {hops(cr_res)}  (attempts: {cr_res['attempts']})  -> {render_crossref(v['crossref'])}")
    if cr_res.get("agency"):
        print(f"                 registration agency: {cr_res['agency']} (api.crossref.org/works/<doi>/agency)")
    if meta:
        year = ((meta.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        authors = "; ".join(a.get("family") or a.get("literal") or "?" for a in (meta.get("author") or [])[:3])
        print(f"                 registered: {meta.get('container-title') or '-'} | {year} | "
              f"{meta.get('type') or '-'} | authors: {authors or '-'}")
    if v["openalex"]:
        print(f"      openalex:  -> {render_openalex(v['openalex'])}")
    print(f"      landing:   {hops(land_res) if land_res else '(skipped)'}  -> {render_landing(v['landing'])}")
    return v


def verify_markdown(table, columns, landing, tally):
    """Markdown 证据表：逐行核验，把文字写回 verified 列（表外内容不变）。"""
    lines = read_text(table).splitlines()
    header = next((i for i, l in enumerate(lines)
                   if (c := split_row(l)) and find_column(c, "verified", columns) is not None
                   and find_column(c, "id", columns) is not None), None)
    if header is None:
        sys.exit(t("verify.no_header", table=table))
    cols = split_row(lines[header])
    i_doi, i_ver = find_column(cols, "id", columns), find_column(cols, "verified", columns)
    i_rank, i_title = find_column(cols, "rank", columns), find_column(cols, "title", columns)  # 中文或英文表头
    i = header + 2  # 跳过表头下面的分隔行
    while i < len(lines) and (cells := split_row(lines[i])) is not None:
        rank = cells[i_rank] if i_rank is not None else str(i)
        v = verify_and_print(rank, cells[i_doi], cells[i_title] if i_title is not None else "", landing)
        tally.add(v)
        cells[i_ver] = render_verified(v).replace("|", "\\|")
        lines[i] = "| " + " | ".join(cells) + " |"
        i += 1
    write_text(table, "\n".join(lines) + "\n")
    print(f"written: verified column in {table}")


def verify_json(table, cfg, landing, tally, root):
    """证据 JSON：把结构化结果写进 rows[].verification，再按 JSON 重新生成 Markdown（Markdown 被手工改过时不覆盖）。"""
    try:
        doc = evidence.load(table, cfg)
    except evidence.EvidenceError as e:
        sys.exit(str(e))
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for row in doc["rows"]:
        v = verify_and_print(row.get("rank"), f"doi:{row['doi']}" if row.get("doi") else "", row.get("title") or "", landing)
        tally.add(v)
        row["verification"] = {**v, "checked_at": checked_at}
        row.pop("verified_text", None)
    write_json(table, doc)
    print(t("evidence.written", path=table))
    md = doc["meta"].get("markdown")
    if md:
        md_path = (root / md) if not Path(md).is_absolute() else Path(md)
        if evidence.markdown_was_edited(doc, md_path):
            print(t("evidence.md_edited", path=md), file=sys.stderr)
            return
        text = evidence.render_markdown(doc)
        write_text(md_path, text)
        evidence.mark_rendered(doc, text)
        write_json(table, doc)
        print(t("evidence.written", path=md))


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Verify DOIs in the evidence table via doi.org and Crossref.")
    ap.add_argument("--table", type=Path, default=None, help=t("verify.arg.table"))
    ap.add_argument("--no-landing", action="store_true", help=t("verify.arg.no_landing"))
    runtime.add_common_args(ap, network=True)
    args = ap.parse_args()
    rt = runtime.init(args)
    runtime.bind_root(globals(), rt.root, {"DEFAULT_TABLE": "evidence/evidence_table.md"})
    cfg, client = rt.cfg, rt.client
    table = args.table or DEFAULT_TABLE
    landing = not args.no_landing and cfg["verify"]["landing"]
    print(f"verify run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}  table={table}")
    tally = Tally()
    if table.suffix.lower() == ".json":
        verify_json(table, cfg, landing, tally, rt.root)
    else:
        verify_markdown(table, cfg["columns"], landing, tally)
    print("\nhttp: " + json.dumps(client.stats_summary(), ensure_ascii=False))
    print("summary crossref: " + " | ".join(f"{k}: {v}" for k, v in sorted(tally.cr.items())))
    print("summary landing:  " + " | ".join(f"{k}: {v}" for k, v in sorted(tally.land.items())))
    return 1 if tally.failed else 0


if __name__ == "__main__":
    sys.exit(main())
