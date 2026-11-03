"""API 响应与本项目文件的形状校验（不依赖 jsonschema）。

每个校验函数接受解析后的对象，返回警告字符串列表（空列表 = 通过）。客户端把警告记在 meta.http 里，不中断研究运行；
测试里对录制件逐条运行同样的校验，API 改字段名时测试会失败。形状来自 2026-11-02 的实测与官方文档（见 docs/ARCHITECTURE_REVIEW.md）。
"""


def expect(obj, path, types, nullable=False, out=None):
    """obj[path] 的类型是否为 types（元组）；路径用 . 分隔，列表元素用 []。把问题追加到 out。"""
    out = out if out is not None else []
    cur = obj
    for part in path.split("."):
        if part == "":
            continue
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            out.append(f"missing {path}")
            return out
    if cur is None:
        if not nullable:
            out.append(f"{path} is null")
    elif not isinstance(cur, types):
        out.append(f"{path} is {type(cur).__name__}, expected {'/'.join(t.__name__ for t in types)}")
    return out


def openalex_list(obj):
    w = []
    expect(obj, "meta", (dict,), out=w)
    expect(obj, "meta.count", (int,), out=w)
    expect(obj, "results", (list,), out=w)
    if isinstance(obj.get("meta"), dict):
        m = obj["meta"]
        if "x_query" in m:
            expect(m, "x_query.oql", (str,), nullable=True, out=w)
            expect(m, "x_query.oqo", (dict,), nullable=True, out=w)
        if m.get("per_page") is not None and isinstance(obj.get("results"), list) and len(obj["results"]) > m["per_page"]:
            w.append("results longer than per_page")
    for i, work in enumerate((obj.get("results") or [])[:50]):
        w.extend(f"results[{i}]: {x}" for x in openalex_work(work))
    return w


def openalex_work(work):
    w = []
    if not isinstance(work, dict):
        return ["work is not an object"]
    expect(work, "id", (str,), out=w)
    if isinstance(work.get("id"), str) and not work["id"].startswith("https://openalex.org/W"):
        w.append("id does not look like an OpenAlex work id")
    if "doi" in work:
        expect(work, "doi", (str,), nullable=True, out=w)
        if isinstance(work.get("doi"), str) and not work["doi"].lower().startswith("https://doi.org/"):
            w.append("doi is not a https://doi.org/ URL")
    for k, t in (("display_name", (str,)), ("title", (str,)), ("publication_year", (int,)),
                 ("abstract_inverted_index", (dict,)), ("primary_location", (dict,)), ("referenced_works", (list,)),
                 ("cited_by_count", (int,)), ("type", (str,)), ("authorships", (list,)), ("locations", (list,))):
        if k in work:
            expect(work, k, t, nullable=True, out=w)
    return w


def s2_bulk(obj):
    w = []
    expect(obj, "total", (int,), out=w)
    expect(obj, "token", (str,), nullable=True, out=w)
    expect(obj, "data", (list,), out=w)
    data = obj.get("data") or []
    if isinstance(data, list) and len(data) > 1000:
        w.append("more than 1000 records in one bulk page")
    for i, p in enumerate(data[:50]):
        w.extend(f"data[{i}]: {x}" for x in s2_paper(p))
    return w


def s2_paper(p):
    w = []
    if not isinstance(p, dict):
        return ["paper is not an object"]
    expect(p, "paperId", (str,), nullable=True, out=w)
    for k, t in (("externalIds", (dict,)), ("title", (str,)), ("year", (int,)), ("abstract", (str,)), ("venue", (str,)),
                 ("journal", (dict,)), ("citationCount", (int,)), ("authors", (list,))):
        if k in p:
            expect(p, k, t, nullable=True, out=w)
    return w


def s2_batch(obj, n_ids=None):
    if not isinstance(obj, list):
        return ["batch response is not a list"]
    w = []
    if n_ids is not None and len(obj) != n_ids:
        w.append(f"batch returned {len(obj)} items for {n_ids} ids")
    for i, p in enumerate(obj[:50]):
        if p is not None:
            w.extend(f"[{i}]: {x}" for x in s2_paper(p))
    return w


def s2_citations(obj):
    w = []
    expect(obj, "data", (list,), out=w)
    if "offset" in obj:
        expect(obj, "offset", (int,), out=w)
    if "next" in obj:
        expect(obj, "next", (int,), nullable=True, out=w)
    for i, c in enumerate((obj.get("data") or [])[:50]):
        if not isinstance(c, dict) or not isinstance(c.get("citingPaper", c.get("citedPaper")), dict):
            w.append(f"data[{i}]: missing citingPaper/citedPaper")
    return w


def crossref_work(obj):
    w = []
    expect(obj, "status", (str,), out=w)
    expect(obj, "message", (dict,), out=w)
    m = obj.get("message") or {}
    if isinstance(m, dict):
        expect(m, "DOI", (str,), out=w)
        expect(m, "title", (list,), nullable=True, out=w)
        expect(m, "type", (str,), nullable=True, out=w)
        if "issued" in m:
            expect(m, "issued.date-parts", (list,), nullable=True, out=w)
    return w


def crossref_agency(obj):
    w = []
    expect(obj, "message.agency.id", (str,), out=w)
    agency = ((obj.get("message") or {}).get("agency") or {}).get("id")
    if agency and agency not in ("crossref", "datacite", "medra", "public", "kisti", "jalc", "op", "istic", "airiti", "cnki"):
        w.append(f"unknown agency {agency!r}")
    return w


def csl_json(obj):
    w = []
    if not isinstance(obj, dict):
        return ["CSL JSON is not an object"]
    for k, t in (("title", (str,)), ("type", (str,)), ("container-title", (str,)), ("author", (list,)), ("issued", (dict,))):
        if k in obj:
            expect(obj, k, t, nullable=True, out=w)
    return w


# ---------- 本项目的文件 ----------

RAW_RECORD_FIELDS = ("title", "year", "doi", "arxiv_id", "venue", "abstract", "source_api", "query_id")


def raw_results_file(obj):
    """results/raw/{source}_{Qn}{suffix}.json。"""
    w = []
    expect(obj, "meta", (dict,), out=w)
    expect(obj, "records", (list,), out=w)
    m = obj.get("meta") or {}
    for k in ("source_api", "query_id", "query_original"):
        expect(m, k, (str,), nullable=(k == "query_original"), out=w)
    for i, r in enumerate(obj.get("records") or []):
        if not isinstance(r, dict):
            w.append(f"records[{i}] is not an object")
            continue
        missing = [k for k in RAW_RECORD_FIELDS if k not in r]
        if missing:
            w.append(f"records[{i}] missing {missing}")
        if r.get("year") is not None and not isinstance(r["year"], int):
            w.append(f"records[{i}].year is not int")
        if not r.get("doi") and not r.get("arxiv_id") and not r.get("title"):
            w.append(f"records[{i}] has neither identifier nor title")
    return w
