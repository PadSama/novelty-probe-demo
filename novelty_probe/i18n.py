"""界面文案的中英文消息表（不用 gettext：约百条消息，不值得 .po/.mo 的编译流程）。

语言：命令行 --lang > 环境变量 NP_LANG > 配置 language > zh。
t(key, **kw) 取当前语言的文案并格式化；缺少某语言时退回中文，再退回键名本身（便于发现漏翻）。
数据文件里不放展示文字：verify 写入证据 JSON 的是结构化结果，展示时再按语言渲染（见 novelty_probe/evidence.py）。
"""
import os
import sys

_LANG = [os.environ.get("NP_LANG") if os.environ.get("NP_LANG") in ("zh", "en") else "zh"]

MESSAGES = {
    # ---- 通用参数 ----
    "arg.root": {"zh": "项目根目录（默认：环境变量 NOVELTY_PROBE_ROOT，或从当前目录向上找 novelty-probe.json / PROJECT.md）",
                 "en": "Project root (default: $NOVELTY_PROBE_ROOT, or the nearest folder upwards with novelty-probe.json / PROJECT.md)"},
    "arg.config": {"zh": "配置文件（默认：环境变量 NOVELTY_PROBE_CONFIG，或项目根目录下的 novelty-probe.json）",
                   "en": "Config file (default: $NOVELTY_PROBE_CONFIG, or novelty-probe.json in the project root)"},
    "arg.lang": {"zh": "界面语言 zh / en（默认：环境变量 NP_LANG，或配置里的 language）",
                 "en": "Interface language zh / en (default: $NP_LANG, or language in the config)"},
    "arg.http_mode": {"zh": "live（默认）每次请求网络；cache 先查缓存；record 边请求边录制；replay 只从录制件回放、不联网。也可用环境变量 NP_HTTP_MODE",
                      "en": "live (default) always uses the network; cache reads the cache first; record also writes a cassette; replay only plays a cassette, no network. Also $NP_HTTP_MODE"},
    "arg.cache_dir": {"zh": "缓存目录（默认 .cache/http，或环境变量 NP_HTTP_CACHE）",
                      "en": "Cache directory (default .cache/http, or $NP_HTTP_CACHE)"},
    "arg.cassette": {"zh": "录制件路径（record / replay 模式；或环境变量 NP_HTTP_CASSETTE）",
                     "en": "Cassette path (record / replay modes; or $NP_HTTP_CASSETTE)"},
    "arg.refresh": {"zh": "cache 模式下忽略已有缓存，重新请求", "en": "In cache mode, ignore cached entries and fetch again"},
    "arg.suffix_only": {"zh": "只处理这个后缀的结果文件，如 _v2（默认无后缀，即 v1）",
                        "en": "Only process result files with this suffix, e.g. _v2 (default: no suffix, i.e. v1)"},
    "arg.suffix_out": {"zh": "输出文件名后缀，如 _v2", "en": "Suffix for output file names, e.g. _v2"},

    # ---- 文件 ----
    "io.bad_json": {"zh": "{path} 不是合法的 JSON（第 {line} 行）：{msg}", "en": "{path} is not valid JSON (line {line}): {msg}"},

    # ---- 检索式 ----
    "query.unregistered_truncation": {
        "zh": "未登记的截断词 {tok}：请在 novelty-probe.json 的 queries.truncation 中登记它对应的完整词（如 \"{tok}\": \"…\"）",
        "en": "Unregistered truncation {tok}: register its full word under queries.truncation in novelty-probe.json (e.g. \"{tok}\": \"…\")"},
    "query.nested": {"zh": "不支持嵌套括号", "en": "Nested parentheses are not supported"},
    "query.unbalanced": {"zh": "括号不配对", "en": "Unbalanced parentheses"},
    "query.and_in_group": {"zh": "不支持括号内的 AND", "en": "AND inside parentheses is not supported"},
    "query.or_outside": {"zh": "不支持括号外的 OR", "en": "OR outside parentheses is not supported"},
    "query.not_first": {"zh": "检索式不能以 NOT 开头", "en": "A query cannot start with NOT"},
    "query.not_position": {"zh": 'NOT 只能写在 AND 之后、作为一个组的开头，例如 … AND NOT ("a" OR "b")',
                           "en": 'NOT must follow AND and start a group, e.g. … AND NOT ("a" OR "b")'},
    "query.lowercase_operator": {"zh": "运算符必须大写：{tok} → {upper}；如果它是检索词，请加引号",
                                 "en": "Operators must be upper case: {tok} → {upper}; if it is a search term, put it in quotes"},
    "query.negation_prefix": {"zh": "不支持用 {ch} 表示排除（{tok}），请写成 AND NOT (…)",
                              "en": "{ch} cannot be used for exclusion ({tok}); write AND NOT (…)"},
    "query.empty_group": {"zh": "存在空的组（如 ()、连续的 AND，或末尾多出的 AND / NOT）",
                          "en": "Empty group (such as (), two ANDs in a row, or a trailing AND / NOT)"},
    "query.unbalanced_quote": {"zh": "引号不配对：短语要用一对英文双引号括起来", "en": "Unbalanced quote: a phrase needs a pair of straight double quotes"},
    "query.empty_phrase": {"zh": '空的短语 ""', "en": 'Empty phrase ""'},
    "query.missing_or": {"zh": "括号内的检索词之间要写 OR", "en": "Terms inside parentheses must be joined by OR"},
    "query.missing_and": {"zh": "组与组之间缺少 AND（短语请加英文双引号）", "en": "Missing AND between groups (put phrases in straight double quotes)"},
    "query.dangling_or": {"zh": "OR 的两侧都要有检索词", "en": "OR needs a term on both sides"},
    "query.truncation_position": {"zh": "截断符 * 只能出现一次，并且放在词尾：{tok}", "en": "The truncation mark * may appear once, at the end of a word: {tok}"},
    "query.where": {"zh": "（{code}，第 {col} 个字符）", "en": " ({code}, at character {col})"},
    "query.where_code": {"zh": "（{code}）", "en": " ({code})"},
    "query.no_include": {"zh": "至少需要一个不带 NOT 的组", "en": "At least one group without NOT is required"},
    "query.comma": {"zh": "检索式里不能有逗号（OpenAlex 的 filter 用逗号分隔条件）",
                    "en": "A query cannot contain a comma (OpenAlex separates filter conditions with commas)"},
    "openalex.quoted_operators": {"zh": "OpenAlex 把运算符当成了检索词（检索式可能有未配对的引号或括号；oql: {oql}），结果未保存",
                                  "en": "OpenAlex treated an operator as a search term (the query may have an unbalanced quote or parenthesis; oql: {oql}); results not saved"},
    "openalex.no_not": {"zh": "OpenAlex 没有把排除组解析为 NOT（oql: {oql}），结果未保存",
                        "en": "OpenAlex did not parse the exclusion group as NOT (oql: {oql}); results not saved"},
    "openalex.term_mismatch": {"zh": "OpenAlex 解析出的检索词与发送的不同：多出 {extra}，缺少 {missing}",
                               "en": "Terms parsed by OpenAlex differ from those sent: extra {extra}, missing {missing}"},

    # ---- 检索式文件 ----
    "queries.not_array": {"zh": "{path} 应为非空的 JSON 数组", "en": "{path} must be a non-empty JSON array"},
    "queries.item": {"zh": "第 {i} 条", "en": "item {i}"},
    "queries.not_object": {"zh": "第 {i} 条不是对象", "en": "item {i} is not an object"},
    "queries.bad_id": {"zh": "第 {i} 条的 id {qid} 应为 Q1、Q2 这样的格式（{pattern}）",
                       "en": "item {i}: id {qid} must look like Q1, Q2 ({pattern})"},
    "queries.duplicate_id": {"zh": "id {qid} 重复", "en": "duplicate id {qid}"},
    "queries.missing_query": {"zh": "{who} 缺少 query", "en": "{who} has no query"},
    "queries.bad_purpose": {"zh": "{who} 的 purpose {purpose} 应为 {allowed} 之一", "en": "{who}: purpose {purpose} must be one of {allowed}"},
    "queries.problems": {"zh": "检索式文件有问题：", "en": "Problems in the queries file:"},

    # ---- search.py ----
    "search.arg.ids": {"zh": "只跑这些检索式，逗号分隔，如 Q1,Q3", "en": "Run only these queries, comma-separated, e.g. Q1,Q3"},
    "search.arg.sources": {"zh": "逗号分隔：openalex,semanticscholar（默认：配置中启用的来源）",
                           "en": "Comma-separated: openalex,semanticscholar (default: sources enabled in the config)"},
    "search.arg.queries": {"zh": "检索式文件，默认 queries/queries.json", "en": "Queries file, default queries/queries.json"},
    "search.arg.dry_run": {"zh": "不联网：只检查检索式语法并打印各来源实际会发送的检索串",
                           "en": "Offline: only check query syntax and print the strings each source would receive"},
    "search.unknown_ids": {"zh": "检索式文件中没有这些 id：{ids}", "en": "These ids are not in the queries file: {ids}"},
    "search.unknown_sources": {"zh": "未知来源：{names}", "en": "Unknown sources: {names}"},
    "search.summary": {"zh": "{ok}/{total} 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 {top_n} 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。",
                       "en": "{ok}/{total} requests succeeded. total_hits = API-reported matches; saved = records kept (top {top_n}: OpenAlex by API relevance, S2 re-ranked locally by relevance); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED)."},
    "search.plan": {"zh": "请求估算（上限）：{lines}", "en": "Request estimate (upper bound): {lines}"},
    "search.plan_source": {"zh": "{name} 最多 {n} 个请求", "en": "{name} at most {n} requests"},
    "search.plan_credits": {"zh": "（OpenAlex 约 {credits} credits）", "en": " (about {credits} OpenAlex credits)"},
    "search.credit_warning": {"zh": "OpenAlex 剩余额度 {remaining} credits，不够完成余下 {n} 个请求（约 {need} credits）；可以先停下，额度恢复后用 --ids 补跑",
                              "en": "OpenAlex has {remaining} credits left, not enough for the remaining {n} requests (about {need} credits); consider stopping and re-running later with --ids"},
    "search.skipped": {"zh": "SKIPPED（{reason}）", "en": "SKIPPED ({reason})"},
    "search.hyphen_hint": {"zh": "提示：{terms} 含连字符却没加引号；Semantic Scholar 会把它当作短语，OpenAlex 的处理可能不同，建议加英文双引号",
                           "en": "hint: {terms} contain a hyphen but no quotes; Semantic Scholar treats them as phrases while OpenAlex may not, so consider quoting them"},
    "openalex.group_mismatch": {"zh": "OpenAlex 对检索式的分组与发送的不同（发送：{sent}；OpenAlex：{got}），结果未保存",
                                "en": "OpenAlex grouped the query differently from what was sent (sent: {sent}; OpenAlex: {got}); results not saved"},
    "openalex.unknown_tree": {"zh": "OpenAlex 的解析树结构无法识别，未能逐组核对，只比较了检索词集合",
                              "en": "The structure of OpenAlex's parse tree was not recognized; groups could not be checked, only the term set was compared"},
    "search.dry_summary": {"zh": "{ok}/{total} queries valid（dry run，未发送任何请求）", "en": "{ok}/{total} queries valid (dry run, nothing sent)"},

    # ---- merge.py / qa.py / compare.py ----
    "merge.arg.legacy": {"zh": "用 Step 6 / Step 14 当时的方法（按命中次数排序、只按完全相同的标题合并），复现已提交的 v1、v2 结果",
                         "en": "Use the method of Steps 6 / 14 (rank by hits, merge only identical titles) to reproduce the committed v1/v2 results"},
    "merge.no_records": {"zh": "results/raw/ 中没有后缀为 '{suffix}' 的记录", "en": "No records with suffix '{suffix}' in results/raw/"},
    "merge.mixed_methods": {"zh": "results/raw/ 中同一来源混有不同检索方式的结果，请先重跑 search.py：{mixed}",
                            "en": "results/raw/ mixes results from different search methods for one source; re-run search.py first: {mixed}"},
    "qa.no_files": {"zh": "results/raw/ 中没有后缀为 '{suffix}' 的结果文件", "en": "No result files with suffix '{suffix}' in results/raw/"},
    "compare.arg.runs": {"zh": '逗号分隔的后缀，v1 写空字符串，如 ",_v1b"', "en": 'Comma-separated suffixes; v1 is the empty string, e.g. ",_v1b"'},
    "compare.arg.known": {"zh": "逗号分隔的已知文献 DOI 或 arXiv:<ID>", "en": "Comma-separated DOIs or arXiv:<ID> of known papers"},
    "compare.arg.ignore": {"zh": "判断 noise 时不计入匹配的短语，如 '\"narrow AI\"'", "en": "Phrases not counted as matches when judging noise, e.g. '\"narrow AI\"'"},
    "compare.arg.markers": {"zh": "标记词组的名称（配置 compare.marker_terms；默认 compare.default_markers）",
                            "en": "Name of the marker term set (config compare.marker_terms; default compare.default_markers)"},
    "compare.arg.out": {"zh": "把结果另存为 JSON", "en": "Also save the report as JSON"},
    "compare.unknown_markers": {"zh": "配置中没有标记词组 {name}（可用：{names}）", "en": "No marker set {name} in the config (available: {names})"},
    "compare.missing_merged": {"zh": "{name}: 找不到合并结果：{file}", "en": "{name}: merged results not found: {file}"},

    # ---- snowball.py ----
    "snowball.arg.seeds": {"zh": "逗号分隔的 DOI 或 arXiv:<ID>", "en": "Comma-separated DOIs or arXiv:<ID>"},
    "snowball.arg.from_evidence": {"zh": "证据表路径（.md 或 .json）：取至少 --min-overlap 个面为 overlap 的行作种子",
                                   "en": "Evidence table (.md or .json): rows with at least --min-overlap overlapping facets become seeds"},
    "snowball.arg.min_overlap": {"zh": "种子至少要有几个面为 overlap（默认取配置 snowball.min_overlap）",
                                 "en": "Minimum overlapping facets for a seed (default: config snowball.min_overlap)"},
    "snowball.arg.queries": {"zh": "用于计算 query_blocks 的检索式文件", "en": "Queries file used for query_blocks"},
    "snowball.arg.suffix": {"zh": "输出文件后缀，与对应检索结果一致，如 _v2", "en": "Output suffix, matching the search results, e.g. _v2"},
    "snowball.arg.cocite": {"zh": "两步共被引：引用种子的文献（可按 --citer-filter 过滤）共同引用了什么",
                            "en": "Two-hop co-citation: what the papers citing the seeds (optionally filtered by --citer-filter) cite in common"},
    "snowball.arg.citer_filter": {"zh": "共被引模式下过滤引用者的布尔式（标题 + 摘要），如 'scientist*'；写法同检索式",
                                  "en": "Boolean filter on citing papers (title + abstract) in co-citation mode, e.g. 'scientist*'; same syntax as queries"},
    "snowball.arg.min_support": {"zh": "共被引模式：至少被几篇引用者共同引用", "en": "Co-citation: minimum number of citing papers"},
    "snowball.arg.direction": {"zh": "一步模式的方向", "en": "Direction in one-hop mode"},
    "snowball.arg.max_forward": {"zh": "最多取多少条前向引用（一步模式按每个种子计）", "en": "Maximum citing papers to fetch (per seed in one-hop mode)"},
    "snowball.arg.label": {"zh": "输出文件标签，默认一步模式 C1、共被引模式 C2", "en": "Output label; default C1 (one hop) or C2 (co-citation)"},
    "snowball.arg.top": {"zh": "CSV 中每条路径各取前多少条", "en": "Rows per path in the CSV"},
    "snowball.arg.keep": {"zh": "原始结果文件保存排序后的前多少条（全部条数记在 meta）", "en": "Records kept in the raw file after ranking (the total is in meta)"},
    "snowball.plan_pages": {"zh": "OpenAlex 翻页：共 {count} 条，取 {n} 条，约 {pages} 个请求（约 {credits} credits）",
                            "en": "OpenAlex paging: {count} in total, taking {n}: about {pages} requests (about {credits} credits)"},
    "snowball.plan_ids": {"zh": "按 ID 取 {n} 篇的元数据：{batches} 个请求（约 {credits} credits）",
                          "en": "Fetching metadata for {n} works by ID: {batches} requests (about {credits} credits)"},
    "snowball.no_header": {"zh": "{path} 中找不到含 DOI/arXiv 列的表头", "en": "No header with a DOI/arXiv column in {path}"},
    "snowball.no_seeds": {"zh": "没有种子文献", "en": "No seed papers"},

    # ---- verify.py ----
    "verify.arg.table": {"zh": "证据表（.md 或 .json）", "en": "Evidence table (.md or .json)"},
    "verify.arg.no_landing": {"zh": "不检查出版商落地页，只做元数据核验", "en": "Skip publisher landing pages; check metadata only"},
    "verify.no_header": {"zh": "{table} 中找不到含 DOI/arXiv 与 verified 列的表头", "en": "No header with DOI/arXiv and verified columns in {table}"},
    "verify.sep": {"zh": "；", "en": "; "},
    "verify.title_match": {"zh": "题目一致", "en": "title matches"},
    "verify.title_mismatch": {"zh": "题目不一致", "en": "title differs"},
    "verify.title_missing": {"zh": "题目缺失", "en": "no title"},
    "verify.no_crossref_record": {"zh": "Crossref 无记录（{agency} 登记的 DOI）", "en": "Crossref has no record ({agency}-registered DOI)"},
    "verify.openalex_not_indexed": {"zh": " (未收录该 DOI)", "en": " (DOI not indexed)"},
    "verify.landing": {"zh": "落地页", "en": "Landing page"},
    "verify.skipped": {"zh": "skipped", "en": "skipped"},
    "verify.unverified": {"zh": "UNVERIFIED", "en": "UNVERIFIED"},

    # ---- HTTP ----
    "http.replay_miss": {"zh": "录制件中没有这个请求：{method} {url}", "en": "Request not in the cassette: {method} {url}"},
    "http.replay_nearest": {"zh": "（最接近的已录 URL：{near}）", "en": " (nearest recorded URL: {near})"},
    "http.circuit_open": {"zh": "{host} 连续 {n} 次 429，熔断；稍后再试", "en": "{host}: {n} consecutive 429s, circuit open; try again later"},
    "http.bad_mode": {"zh": "NP_HTTP_MODE 应为 {modes} 之一，不是 {mode}", "en": "NP_HTTP_MODE must be one of {modes}, not {mode}"},
    "http.replay_needs_cassette": {"zh": "replay 模式需要指定录制件（NP_HTTP_CASSETTE 或 --cassette）",
                                   "en": "replay mode needs a cassette (NP_HTTP_CASSETTE or --cassette)"},
    "http.not_json": {"zh": "响应不是 JSON（Content-Type: {ctype}）：{summary}", "en": "Response is not JSON (Content-Type: {ctype}): {summary}"},

    # ---- evidence ----
    "evidence.no_table": {"zh": "{path} 中找不到证据表（需要含 DOI/arXiv 与 verified 列的表头）",
                          "en": "No evidence table in {path} (a header with DOI/arXiv and verified columns is required)"},
    "evidence.bad_schema": {"zh": "{path} 不是证据 JSON（schema 应为 {schema}）", "en": "{path} is not an evidence JSON (schema must be {schema})"},
    "evidence.default_title": {"zh": "证据表", "en": "Evidence table"},
    "evidence.heading_table": {"zh": "表", "en": "Table"},
    "evidence.heading_rationale": {"zh": "判定依据", "en": "Rationale"},
    "evidence.check_ok": {"zh": "检查通过：{n} 行，没有发现问题", "en": "Check passed: {n} rows, no problems"},
    "evidence.check_summary": {"zh": "{n} 行：{errors} 个问题，{warnings} 个提醒", "en": "{n} rows: {errors} problems, {warnings} warnings"},
    "evidence.bad_label": {"zh": "rank {rank}：{facet} 的取值 {value!r} 不在 {labels} 中", "en": "rank {rank}: {facet} value {value!r} is not one of {labels}"},
    "evidence.missing_facet": {"zh": "rank {rank}：缺少面 {facet} 的标注", "en": "rank {rank}: no label for facet {facet}"},
    "evidence.duplicate_rank": {"zh": "rank {rank} 重复", "en": "duplicate rank {rank}"},
    "evidence.duplicate_work": {"zh": "rank {rank} 与 rank {other} 的标识符相同（同一篇文献出现两次？）",
                                "en": "rank {rank} shares an identifier with rank {other} (the same work twice?)"},
    "evidence.no_identifier": {"zh": "rank {rank}：既没有 DOI 也没有 arXiv ID（应标 UNVERIFIED，规则 2）",
                               "en": "rank {rank}: neither DOI nor arXiv ID (should be marked UNVERIFIED, rule 2)"},
    "evidence.id_not_retrieved": {"zh": "rank {rank}：{ident} 不在检索结果中（规则 2：标识符只能来自检索结果）",
                                  "en": "rank {rank}: {ident} is not in the retrieval results (rule 2: identifiers must come from retrieval results)"},
    "evidence.merged_id_mismatch": {"zh": "rank {rank}：判定依据标题写的是 {heading}，检索结果中这篇是 {record}（合并结果文件对不上？）",
                                    "en": "rank {rank}: the rationale heading says {heading}, but this work is {record} in the results (wrong merged file?)"},
    "evidence.title_mismatch": {"zh": "rank {rank}：题目与检索结果不同（检索结果：{record}）", "en": "rank {rank}: title differs from the retrieval record ({record})"},
    "evidence.year_mismatch": {"zh": "rank {rank}：年份 {value} 与检索结果的 {record} 不同", "en": "rank {rank}: year {value} differs from {record} in the retrieval results"},
    "evidence.authors_mismatch": {"zh": "rank {rank}：作者与 authors.py 的结果不同（应为：{record}）",
                                  "en": "rank {rank}: authors differ from the authors.py result (expected: {record})"},
    "evidence.unbalanced_quotes": {"zh": "rank {rank}：判定依据中有 {n} 行引号个数为奇数，这些行的引文未检查",
                                   "en": "rank {rank}: {n} rationale lines have an odd number of quotes; their quotes were not checked"},
    "evidence.quote_not_found": {"zh": "rank {rank}：引文不是摘要原文：\"{quote}\"", "en": "rank {rank}: quote is not verbatim from the abstract: \"{quote}\""},
    "evidence.no_abstract": {"zh": "rank {rank}：检索结果中找不到这篇的摘要，{n} 处引文无法核对",
                             "en": "rank {rank}: no abstract for this work in the retrieval results; {n} quotes cannot be checked"},
    "evidence.no_results": {"zh": "没有找到检索结果文件（--results），只做了不依赖检索结果的检查",
                            "en": "No retrieval results file found (--results); only checks that do not need it were run"},
    "evidence.using": {"zh": "检索结果：{results}；补充摘要：{enrichment}；作者：{authors}", "en": "results: {results}; enrichment: {enrichment}; authors: {authors}"},
    "evidence.roundtrip_exact": {"zh": "还原检查：按 JSON 重新生成的 Markdown 与原文件逐字相同", "en": "Round trip: Markdown regenerated from the JSON is identical to the original"},
    "evidence.roundtrip_diff": {"zh": "还原检查：重新生成的 Markdown 有 {n} 行与原文件不同（第一处在第 {line} 行）",
                                "en": "Round trip: {n} lines of the regenerated Markdown differ from the original (first at line {line})"},
    "evidence.kept_verification": {"zh": "沿用了 {n} 行的结构化核验结果（来自原有的 {path}）", "en": "Kept structured verification for {n} rows (from the existing {path})"},
    "evidence.md_edited": {"zh": "{path} 在上次导入或渲染后被手工改过，未覆盖。先运行 evidence.py import-md 把改动导入 JSON，或加 --force",
                           "en": "{path} was edited by hand after the last import or render; not overwritten. Run evidence.py import-md first, or pass --force"},
    "evidence.written": {"zh": "已写入：{path}", "en": "written: {path}"},
    "evidence.arg.action": {"zh": "import-md：Markdown → JSON；render：JSON → Markdown；check：检查（.json 或 .md）",
                            "en": "import-md: Markdown → JSON; render: JSON → Markdown; check: run the checks (.json or .md)"},
    "evidence.arg.file": {"zh": "证据文件", "en": "Evidence file"},
    "evidence.arg.out": {"zh": "输出路径（import-md 默认同名 .json；render 默认 meta.markdown 或同名 .md）",
                         "en": "Output path (import-md: same name with .json; render: meta.markdown or same name with .md)"},
    "evidence.arg.results": {"zh": "合并结果 merged*.json（默认按证据表文件名的后缀推断，如 evidence_table_v2 → merged_v2.json）",
                             "en": "Merged results merged*.json (default: inferred from the evidence file suffix, e.g. evidence_table_v2 → merged_v2.json)"},
    "evidence.arg.authors": {"zh": "authors.py 的输出（默认按后缀推断，如 authors_v2.json）", "en": "authors.py output (default: inferred from the suffix, e.g. authors_v2.json)"},
    "evidence.arg.enrichment": {"zh": "enrich.py 的输出（默认 evidence/enrichment*.json 全部）", "en": "enrich.py outputs (default: all evidence/enrichment*.json)"},
    "evidence.arg.force": {"zh": "render 时即使 Markdown 被手工改过也覆盖", "en": "With render: overwrite the Markdown even if it was edited by hand"},
}


def set_language(lang):
    _LANG[0] = lang if lang in ("zh", "en") else "zh"


def get_language():
    return _LANG[0]


def t(key, **kw):
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(_LANG[0]) or entry.get("zh") or key
    return text.format(**kw) if kw else text


def tr(zh, en, **kw):
    """一次性的文案：直接给出中英文两种写法，按当前语言取一种。"""
    text = en if _LANG[0] == "en" else zh
    return text.format(**kw) if kw else text


def early_language(argv=None, env=None):
    """在 argparse 之前确定语言（帮助文本要用）：--lang > NP_LANG > 配置 language > zh。"""
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    for i, a in enumerate(argv):
        if a == "--lang" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--lang="):
            return a.split("=", 1)[1]
    if env.get("NP_LANG") in ("zh", "en"):
        return env["NP_LANG"]
    try:
        from .config import find_config_file
        from .io import load_json_lenient
        from .paths import find_root
        root = None
        explicit = None
        for i, a in enumerate(argv):
            if a == "--root" and i + 1 < len(argv):
                root = argv[i + 1]
            if a == "--config" and i + 1 < len(argv):
                explicit = argv[i + 1]
        f = find_config_file(explicit, find_root(root, env=env), env)
        if f is not None and f.is_file():
            lang = (load_json_lenient(f) or {}).get("language")
            if lang in ("zh", "en"):
                return lang
    except Exception:  # noqa: BLE001  语言探测失败不影响运行
        pass
    return "zh"


def prepare(argv=None):
    """脚本 main() 开头调用：在构建参数解析器之前设好语言。"""
    set_language(early_language(argv))
