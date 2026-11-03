"""DOI 核验的结构化结果与展示文字（scripts/verify.py 产生结果，这里按界面语言生成 verified 列的文字）。

结果的形状（写进证据 JSON 的 rows[].verification）：
  {"doi": "10.…", "checked_at": "…",
   "crossref": {"outcome": "found", "http": 200, "title": "…", "title_match": true}
             | {"outcome": "not_registered", "agency": "datacite"}
             | {"outcome": "http", "http": 404, "host": "api.crossref.org"}
             | {"outcome": "failed", "failure": {"kind": "blocked" | "error", "host": "…", "error": "…"}},
   "openalex": null | {"outcome": "found", "title": "…", "title_match": true} | {"outcome": "http", "http": 404}
             | {"outcome": "failed", "error": "…"},
   "landing": {"outcome": "skipped"} | {"outcome": "http", "http": 200, "host": "…", "page_title": "…"}
            | {"outcome": "failed", "failure": {…}},
   "metadata_ok": true}
没有 DOI 的行：{"doi": null}，显示为 UNVERIFIED。中文文字与改造前的 verify.py 逐字相同（测试与录制件依赖）。
"""
import html
import re

from .i18n import t

_TAG_RE = re.compile(r"<[^>]+>")


def clean(text, limit=None):
    """去 HTML 标签与多余空白；给了 limit 就截短（只用于显示，比对题目时用完整文本）。"""
    text = " ".join(html.unescape(_TAG_RE.sub(" ", text or "")).split())
    return (text[:limit] + "…") if limit and len(text) > limit else text


def render_failure(f):
    if f["kind"] == "blocked":
        return f"BLOCKED at {f['host']} (network policy, proxy 403)"
    return f"ERROR at {f['host']}: {f['error'][:80]}"


def flag(match):
    return t("verify.title_match") if match else (t("verify.title_mismatch") if match is False else t("verify.title_missing"))


def render_crossref(r):
    o = r["outcome"]
    if o == "not_registered":
        return t("verify.no_crossref_record", agency=r["agency"].capitalize())
    if o == "failed":
        return "Crossref " + render_failure(r["failure"])
    if o == "http":
        return f"Crossref HTTP {r['http']} ({r['host']})"
    return f"Crossref HTTP 200 · {flag(r['title_match'])} · {clean(r['title'], 120) or '(no title)'}"


def render_openalex(r):
    o = r["outcome"]
    if o == "http":
        return f"OpenAlex HTTP {r['http']}" + (t("verify.openalex_not_indexed") if r["http"] == 404 else "")
    if o == "failed":
        return f"OpenAlex ERROR: {r['error'][:80]}"
    return f"OpenAlex · {flag(r['title_match'])} · {clean(r['title'], 120) or '(no title)'}"


def render_landing(r):
    label = t("verify.landing")
    o = r["outcome"]
    if o == "skipped":
        return f"{label} {t('verify.skipped')}"
    if o == "failed":
        return f"{label} {render_failure(r['failure'])}"
    return f"{label} HTTP {r['http']} ({r['host']}) · {r['page_title'] or '(no <title>)'}"


def render_verified(v):
    """结构化结果 → verified 列的文字（当前界面语言）。v 为空或没有 DOI：UNVERIFIED。"""
    if not v or not v.get("doi"):
        return t("verify.unverified")
    parts = [render_crossref(v["crossref"])]
    if v.get("openalex"):
        parts.append(render_openalex(v["openalex"]))
    parts.append(render_landing(v["landing"]))
    return t("verify.sep").join(parts)


def tally_keys(v):
    """终端汇总用的分类：元数据一项（题目一致 / OpenAlex 题目一致 / 失败原因）与落地页一项。"""
    cr, oa = v["crossref"], v.get("openalex")
    if cr["outcome"] == "found":
        key_cr = flag(cr["title_match"])
    elif oa and oa["outcome"] == "found":
        key_cr = "OpenAlex " + flag(oa["title_match"])
    else:
        key_cr = render_crossref(cr).split(" (")[0]
    return key_cr, render_landing(v["landing"]).split(" (")[0]
