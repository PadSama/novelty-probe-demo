# RUN_LOG

> 只追加，不改写。每条记录：时间 / 步骤 / 命令 / 产出文件。

---

## [2026-10-31 09:52 UTC] Step 0 — 项目初始化（未检索）

**命令**

```bash
mkdir -p idea facets queries results/raw results/merged evidence logs
touch facets/.gitkeep queries/.gitkeep results/raw/.gitkeep results/merged/.gitkeep evidence/.gitkeep
# 写入 PROJECT.md、idea/idea.md、logs/RUN_LOG.md
```

**产出文件**

- `PROJECT.md` — 角色定义与三条硬规则
- `idea/idea.md` — 研究想法原文（原样保存）
- `logs/RUN_LOG.md` — 本日志
- `facets/` `queries/` `results/raw/` `results/merged/` `evidence/` — 空目录（含 .gitkeep 占位）

**备注**：本步未执行任何文献检索。

---

## [2026-10-31 10:02 UTC] Step 1 — 拆解想法、设计检索词与检索式（未检索）

**命令**

```bash
cat idea/idea.md
cat PROJECT.md
# 写入 facets/facets.md（五个面，每面 5 个检索词）
# 写入 queries/queries.json（6 条检索式）
python3 - <<'PY'   # 内联校验脚本，未存为文件
# 检查：JSON 合法、6 条、字段只有 id/facets_used/query/purpose、purpose 取值合法；
#       每个面 3–5 个词；检索式中的词都来自 facets.md；facets_used 与实际用到的面一致；
#       所有检索词至少用到一次
PY
```

**校验结果**：全部通过。5 个面各 5 个词；Q1–Q6 的 facets_used 与实际用到的面一致；25/25 个检索词均被使用。

**产出文件**

- `facets/facets.md` — 五个面（研究问题 / 作用机制 / 研究情境 / 数据与方法 / 预期发现）及检索词，含类型标注、混淆提示、purpose 约定
- `queries/queries.json` — 6 条检索式：component ×2、application ×2、method ×1、concurrent ×1

**备注**：本步未执行任何文献检索，未列任何文献。"AI 工具"的范围（只指生成式 AI，还是也含机器学习方法）待研究者确认，见 `facets/facets.md` F3。

---

## [2026-10-31 10:16 UTC] Step 2 — 编写并运行检索脚本（两个 API 被网络策略拦截，未取得结果）

**研究者决定（本轮）**

- "AI 工具"只指生成式 AI（2022 年底以后）。
- 筛选时结合产品与公司关键词：LLM、ChatGPT、Gemini、Claude、OpenAI、Anthropic 等。
- 已记入 `facets/facets.md` F3；concurrent 检索式只取 2023 年起的文献。检索式本身未改。

**命令 1：连通性探测**

```bash
curl -sS -m 30 "https://api.openalex.org/works?search=bibliometrics&per-page=1&select=id"
curl -sS -m 30 "https://api.semanticscholar.org/graph/v1/paper/search?query=bibliometrics&limit=1&fields=title"
curl -sS "$HTTPS_PROXY/__agentproxy/status"
```

输出：

```
curl: (56) CONNECT tunnel failed, response 403      # api.openalex.org
curl: (56) CONNECT tunnel failed, response 403      # api.semanticscholar.org
api.openalex.org:443 | gateway answered 403 to CONNECT (policy denial or upstream failure)
api.semanticscholar.org:443 | gateway answered 403 to CONNECT (policy denial or upstream failure)
```

**命令 2：编写脚本、更新文档**

```
# 写入 scripts/search.py
# 更新 facets/facets.md：F3 记录研究者决定；concurrent 年份约定改为 2023 年起
```

**命令 3：离线自测（不联网；伪造的 API 返回只写入临时目录，不进 results/）**

```bash
python3 - <<'PY'   # 内联自测脚本，未存为文件
# 1) 打印 6 条检索式在两个来源的转换结果  2) 非法语法必须报错
# 3) 用伪造记录（占位 ID）检查字段提取    4) 用伪造 API 跑完整流程：文件结构、年份过滤、S2 回退
PY
```

结果：ALL PASSED。各检索式实际要发送的检索串：

```
Q1 OpenAlex: ("large language models" OR "generative AI") AND (homogenization OR homogenisation OR "algorithmic monoculture" OR "collective diversity")
   S2 [plain text: all terms]: large language models generative AI homogenization homogenisation algorithmic monoculture collective diversity
   S2 [plain text: first term of each AND group (fallback)]: large language models homogenization
Q2 OpenAlex: ("narrowing of science" OR "topic concentration" OR "topic diversity" OR "research diversification") AND ("science of science" OR bibliometrics)
   S2 [plain text: all terms]: narrowing of science topic concentration topic diversity research diversification science of science bibliometrics
   S2 [plain text: first term of each AND group (fallback)]: narrowing of science science of science
Q3 OpenAlex: ("AI in science" OR "AI for science" OR "large language models" OR "machine learning") AND ("research topic selection" OR "problem choice" OR "direction of science")
   S2 [plain text: all terms]: AI in science AI for science large language models machine learning research topic selection problem choice direction of science
   S2 [plain text: first term of each AND group (fallback)]: AI in science research topic selection
Q4 OpenAlex: ("streetlight effect" OR "Matthew effect" OR "exploration-exploitation") AND ("AI for science" OR "large language models" OR "generative AI") AND scientists
   S2 [plain text: all terms]: streetlight effect Matthew effect exploration exploitation AI for science large language models generative AI scientists
   S2 [plain text: first term of each AND group (fallback)]: streetlight effect AI for science scientists
Q5 OpenAlex: ("LLM-generated text" OR "topic modeling" OR "difference-in-differences") AND ("science of science" OR bibliometrics) AND ("large language models" OR "generative AI")
   S2 [plain text: all terms]: LLM generated text topic modeling difference in differences science of science bibliometrics large language models generative AI
   S2 [plain text: first term of each AND group (fallback)]: LLM generated text science of science large language models
Q6 OpenAlex: ("AI in science" OR "large language models" OR "generative AI") AND ("topic diversity" OR "narrowing of science" OR "collective diversity" OR disruptiveness OR "research diversification") AND (scientists OR "science of science")
   S2 [plain text: all terms]: AI in science large language models generative AI topic diversity narrowing of science collective diversity disruptiveness research diversification scientists science of science
   S2 [plain text: first term of each AND group (fallback)]: AI in science topic diversity scientists
```

**命令 4：真实运行**

```bash
python3 scripts/search.py
```

输出：

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex                 -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q1    component   semanticscholar          -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q2    component   openalex                 -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q2    component   semanticscholar          -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q3    application openalex                 -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q3    application semanticscholar          -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q4    application openalex                 -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q4    application semanticscholar          -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q5    method      openalex                 -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q5    method      semanticscholar          -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q6    concurrent  openalex                 -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden
Q6    concurrent  semanticscholar          -     -     -  FAILED: network error: Tunnel connection failed: 403 Forbidden

0/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
exit code: 1
```

**产出文件**

- `scripts/search.py` — 检索脚本
- `facets/facets.md` — 更新 F3（研究者决定）与 concurrent 年份约定
- `results/raw/` — 本次无新文件（12 个请求全部被拦截）

**备注**

- 两个 API 主机被本云环境的网络策略拒绝（代理返回 403）。未绕过拦截，未改用其他来源，未编造结果。放行后重跑命令 4 即可。
- 检索式转换规则尚未经真实 API 验证（OpenAlex 的布尔与短语写法；S2 只收纯文本、零命中时退回核心词）。首次真实运行后需核对各文件 meta 中的 query_sent 和 total_hits。

---

## [2026-10-31 10:33 UTC] Step 3 — 放行域名后重跑检索（2/12 成功，其余被限流）

研究者已在环境设置中放行 `api.openalex.org` 和 `api.semanticscholar.org`。

**命令 1：连通性复测**

```bash
curl -sS -m 30 -D <headers> "https://api.openalex.org/works?search=bibliometrics&per-page=1&select=id"
curl -sS -m 30 -D - "https://api.semanticscholar.org/graph/v1/paper/search?query=bibliometrics&limit=1&fields=title"
# S2 间隔 5/10/15/20/25 秒再试 5 次
```

输出（摘要）：

```
OpenAlex  HTTP 429  "Insufficient budget. This request has no API key, so it counts against the free daily
          budget shared by everyone on your network's IP address, and that budget is used up ($0 remaining;
          resets at midnight UTC)."   retry-after: 49210   x-ratelimit-remaining: 0
S2        HTTP 429  "Too Many Requests. Please wait and try again or apply for a key for higher rate limits."
          x-amzn-errortype: TooManyRequestsException（无 Retry-After）；10:20:09–10:21:26 共 6 次，全部 429
```

**命令 2：修改 scripts/search.py**

```
# 429 时若服务端要求等待超过 60 秒（如 OpenAlex 每日额度用完）则不重试，直接报错
# 失败信息显示 API 返回的 message 字段
# OpenAlex key 改为 Authorization 请求头发送（不进 URL）；去掉 OPENALEX_MAILTO
```

**命令 3：本地测试（127.0.0.1 测试服务器，不访问外网）**

```bash
python3 -B - <<'PY'   # 内联测试脚本，未存为文件
# 长等待 429 → 立即失败；403 → 立即失败；两次短暂 429 后 200 → 重试成功；
# 设置 OPENALEX_API_KEY 时 key 只出现在请求头，不出现在 URL 和 meta 中
PY
```

结果：ALL PASSED（/budget 不等待即失败；/forbidden 立即失败；/flaky 等待 2、4 秒后成功）。

**命令 4：真实运行（全量）**

```bash
python3 scripts/search.py
```

输出：

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex                 -     -     -  FAILED: HTTP 429: Insufficient budget. This request has no API key, so it counts against the free daily budget shared by everyone on your network's IP address, and that budget is used up ($0 remaining; resets at midnig…
Q1    component   semanticscholar         16    16     1  results/raw/semanticscholar_Q1.json
Q2    component   openalex                 -     -     -  FAILED: HTTP 429: Insufficient budget. This request has no API key, so it counts against the free daily budget shared by everyone on your network's IP address, and that budget is used up ($0 remaining; resets at midnig…
Q2    component   semanticscholar      31539    25     1  results/raw/semanticscholar_Q2.json  [S2 fallback: core terms]
Q3    application openalex                 -     -     -  FAILED: HTTP 429: Insufficient budget. This request has no API key, so it counts against the free daily budget shared by everyone on your network's IP address, and that budget is used up ($0 remaining; resets at midnig…
Q3    application semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form
Q4    application openalex                 -     -     -  FAILED: HTTP 429: Insufficient budget. This request has no API key, so it counts against the free daily budget shared by everyone on your network's IP address, and that budget is used up ($0 remaining; resets at midnig…
Q4    application semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form
Q5    method      openalex                 -     -     -  FAILED: HTTP 429: Insufficient budget. This request has no API key, so it counts against the free daily budget shared by everyone on your network's IP address, and that budget is used up ($0 remaining; resets at midnig…
Q5    method      semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form
Q6    concurrent  openalex                 -     -     -  FAILED: HTTP 429: Insufficient budget. This request has no API key, so it counts against the free daily budget shared by everyone on your network's IP address, and that budget is used up ($0 remaining; resets at midnig…
Q6    concurrent  semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form

2/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
exit code: 1
```

**命令 5：补跑 S2 失败的 4 条**

```bash
python3 scripts/search.py --ids Q3,Q4,Q5,Q6 --sources semanticscholar
```

输出：

```
query purpose     source          total_hits saved no_id  file / note
Q3    application semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form
Q4    application semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form
Q5    method      semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form
Q6    concurrent  semanticscholar          -     -     -  FAILED: HTTP 429: Too Many Requests. Please wait and try again or apply for a key for higher rate limits. https://www.semanticscholar.org/product/api#api-key-form

0/4 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
exit code: 1
```

**命令 6：检查已存结果是否满足原布尔检索式（标题 + 摘要，机器判断）**

```bash
python3 -I -B - <<'PY'   # 内联脚本，未存为文件：每个 AND 组至少命中一个词即视为满足
PY
```

输出：

```
Q1: satisfies original Boolean query on title+abstract: 14/16 (among records with abstract: 14/14)
Q2: satisfies original Boolean query on title+abstract: 0/25 (among records with abstract: 0/15)
```

**产出文件**

- `results/raw/semanticscholar_Q1.json` — 16 条（全部检索词版本）；有 DOI 13 条、有 arXiv ID 4 条、两者皆无 1 条
- `results/raw/semanticscholar_Q2.json` — 25 条（全部检索词版本零命中，退回核心词版本，API 报告 31,539 条命中）；有 DOI 24 条、有 arXiv ID 4 条、两者皆无 1 条
- `scripts/search.py` — 修改（见命令 2）

**备注**

- OpenAlex：6 条全部失败。无 key 请求共用本环境出口 IP 的每日免费额度，已用完。需要 OpenAlex API key（环境变量 `OPENALEX_API_KEY`）。
- S2：Q3–Q6 两轮均失败（匿名共享限流池）。需要 S2 API key（环境变量 `S2_API_KEY`）或稍后再试。
- 检索质量：S2 relevance search 不支持短语与布尔语法。Q2 退回核心词后的 25 条无一满足原检索式，该文件不宜直接作为 Q2 的证据来源，留待研究者决定 S2 的检索方式后重跑。
- 本步未判断新颖性，未在日志中列出具体文献。

---

## [2026-10-31 11:00 UTC] Step 4 — OpenAlex 配置 key、S2 改用 bulk 接口后重跑（12/12 成功）

**研究者决定（本轮）**

- OpenAlex API key 已配置在环境的 Network secrets 中（由代理注入，容器内无环境变量）。
- 同意 S2 改用 `/graph/v1/paper/search/bulk`（支持布尔语法；不按相关度排序，前 25 条按被引次数取）。

**命令 1：连通性复测**

```bash
curl -sS -m 30 -D <headers> "https://api.openalex.org/works?search=bibliometrics&per-page=1&select=id,display_name"
curl -sS -m 60 "https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=bibliometrics&fields=title&sort=citationCount:desc"
```

输出（摘要）：OpenAlex HTTP 200（X-Ratelimit-Limit-Usd: 1，Remaining-Usd: 0.994）；S2 bulk HTTP 200（total 109740）。

**命令 2：语法实测（python3 内联脚本，未存为文件）**

```
S2 bulk total:  bibliometric* 124248 | bibliometrics 109740 | homogeniz* 148491 | homogenization 145726
                "exploration-exploitation" 4637 = "exploration exploitation" 4637 | "narrowing of science" 72
                ("narrowing of science" | "topic diversity") + ("science of science" | bibliometrics) 14
OpenAlex:       bibliometric* -> HTTP 400 "Wildcards (* or ?) require exact (no-stem) search. ... Use the
                search.exact= parameter instead"
                bibliometrics 475260 (oql: get works with bibliometrics in the full text)
                ("large language models" OR "generative AI") AND (homogenization OR "collective diversity") 19321
                (oql: ((stemmed "collective diversity" OR homogenization) AND (stemmed "generative AI" OR
                stemmed "large language models")) in the full text)
```

结论：S2 bulk 支持截断（*）、短语和布尔组合；OpenAlex 不支持通配符（截断词换完整词的做法保留），布尔解析正确，`search=` 匹配全文。

**命令 3：修改 scripts/search.py**

```
# S2 改用 /paper/search/bulk：AND -> +，OR -> |，括号、短语、截断词原样保留；sort=citationCount:desc，取前 25 条
# 去掉纯文本压平与"退回核心词"逻辑
# OpenAlex meta 增加 api_interpretation（x_query.oql）与 sort 字段
```

**命令 4：打印 S2 bulk 转换结果；删除旧接口产生的 S2 文件**

```bash
python3 -B -c "...to_s2_bulk(...)..."   # 6 条转换结果见各文件 meta.query_sent；转换器单测 OK
git rm results/raw/semanticscholar_Q1.json results/raw/semanticscholar_Q2.json   # 旧接口结果，保留在提交 7dfda92 的历史中
```

**命令 5：真实运行（全量）**

```bash
python3 scripts/search.py
```

输出：

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex             21381    25     1  results/raw/openalex_Q1.json
Q1    component   semanticscholar        391    25     0  results/raw/semanticscholar_Q1.json
Q2    component   openalex              1217    25     1  results/raw/openalex_Q2.json
Q2    component   semanticscholar         43    25     0  results/raw/semanticscholar_Q2.json
Q3    application openalex               832    25     3  results/raw/openalex_Q3.json
Q3    application semanticscholar          9     9     0  results/raw/semanticscholar_Q3.json
Q4    application openalex               678    25     2  results/raw/openalex_Q4.json
Q4    application semanticscholar          1     1     0  results/raw/semanticscholar_Q4.json
Q5    method      openalex              3735    25     1  results/raw/openalex_Q5.json
Q5    method      semanticscholar         45    25     1  results/raw/semanticscholar_Q5.json
Q6    concurrent  openalex             31830    25     0  results/raw/openalex_Q6.json  [year>=2023]
Q6    concurrent  semanticscholar         23    23     1  results/raw/semanticscholar_Q6.json  [year>=2023]

12/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25: OpenAlex by relevance, S2 by citation count); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
exit code: 0
```

**命令 6：质量检查 A——字段覆盖与原布尔式符合度（严格匹配原词，python3 内联脚本）**

```
file                      n  doi arXiv neither abstract  bool_ok(all)  bool_ok(with abstract)
openalex_Q1             25   24     4       1       20     21/25         18/20
openalex_Q2             25   24     4       1       17      4/25          4/17
openalex_Q3             25   22     8       3       23      2/25          2/23
openalex_Q4             25   21    11       2       21      0/25          0/21
openalex_Q5             25   24     1       1       19      4/25          4/19
openalex_Q6             25   25     9       0       23      0/25          0/23
semantic_Q1             25   24    16       0       23     22/25         21/23
semantic_Q2             25   25     1       0       20     15/25         15/20
semantic_Q3              9    9     0       0        7      4/9           4/7
semantic_Q4              1    1     0       0        0      0/1           0/0
semantic_Q5             25   23     2       1       21     13/25         12/21
semantic_Q6             23   22     3       1       21      1/23          1/21

total records: 258; neither DOI nor arXiv: 10; distinct DOIs across all files: 227

OpenAlex query interpretation (x_query.oql):
  Q1: get works with ((stemmed "algorithmic monoculture" OR stemmed "collective diversity" OR homogenisation OR homogenization) AND (stemmed "generative AI" OR stemmed "large language models")) in the full text
  Q2: get works with ((stemmed "narrowing of science" OR stemmed "research diversification" OR stemmed "topic concentration" OR stemmed "topic diversity") AND (stemmed "science of science" OR bibliometrics)) in the full text
  Q3: get works with ((stemmed "AI for science" OR stemmed "AI in science" OR stemmed "large language models" OR stemmed "machine learning") AND (stemmed "direction of science" OR stemmed "problem choice" OR stemmed "research topic selection")) in the full text
  Q4: get works with (scientists AND (stemmed "AI for science" OR stemmed "generative AI" OR stemmed "large language models") AND (stemmed "Matthew effect" OR stemmed "exploration-exploitation" OR stemmed "streetlight effect")) in the full text
  Q5: get works with ((stemmed "LLM-generated text" OR stemmed "difference-in-differences" OR stemmed "topic modeling") AND (stemmed "generative AI" OR stemmed "large language models") AND (stemmed "science of science" OR bibliometrics)) in the full text
  Q6: get works since 2023-01-01 with ((stemmed "AI in science" OR stemmed "generative AI" OR stemmed "large language models") AND (stemmed "collective diversity" OR stemmed "narrowing of science" OR stemmed "research diversification" OR stemmed "topic diversity" OR disruptiveness) AND (stemmed "science of science" OR scientists)) in the full text
```

**命令 7：质量检查 B——符合度改用 Porter 词干还原（近似两个 API 的词干匹配）**

```bash
pip install -q --target <scratchpad>/pylib snowballstemmer   # 装在临时目录，不进系统环境、不进仓库
python3 -I -B - <<'PY'   # 内联脚本，未存为文件
PY
```

输出：

```
Boolean conformity on title+abstract, Porter-stemmed (approximates the APIs' stemmed matching)
file                  strict->stemmed (all)   stemmed (with abstract)
openalex_Q1             21/25 -> 21/25         18/20
openalex_Q2              4/25 ->  4/25          4/17
openalex_Q3              2/25 ->  2/25          2/23
openalex_Q4              0/25 ->  0/25          0/21
openalex_Q5              4/25 ->  7/25          7/19
openalex_Q6              0/25 ->  1/25          1/23
semantic_Q1             22/25 -> 24/25         23/23
semantic_Q2             15/25 -> 18/25         18/20
semantic_Q3               4/9 ->  4/9           4/7
semantic_Q4               0/1 ->  0/1           0/0
semantic_Q5             13/25 -> 22/25         21/21
semantic_Q6              1/23 -> 18/23         18/21
```

**命令 8：对照试验——OpenAlex 改用 `filter=title_and_abstract.search`（只匹配标题+摘要；结果只存临时目录，未进 results/）**

```
Q4: title_and_abstract.search count=1 (search= gave 678); top-1 conformity (stemmed): 0/1, with abstract 0/0
     oql: get works with (scientists AND (stemmed "AI for science" OR stemmed "generative AI" OR stemmed "large language models") AND (stemmed "Matthew effect" OR stemmed "exploration-exploitation" OR stemmed "streetlight effect")) in the title or abstract
Q6: title_and_abstract.search count=64 (search= gave 31830); top-25 conformity (stemmed): 22/25, with abstract 22/23
     oql: get works since 2023-01-01 with ((stemmed "AI in science" OR stemmed "generative AI" OR stemmed "large language models") AND (stemmed "collective diversity" OR stemmed "narrowing of science" OR stemmed "research diversification" OR stemmed "topic diversity" OR disruptiveness) AND (stemmed "science of science" OR scientists)) in the title or abstract
```

**产出文件**

- `results/raw/openalex_Q1.json` … `openalex_Q6.json` — 各 25 条（按相关度）
- `results/raw/semanticscholar_Q1.json` … `semanticscholar_Q6.json` — 25 / 25 / 9 / 1 / 25 / 23 条（按被引次数）
- `scripts/search.py` — 修改（见命令 3）

**备注**

- 共 258 条记录，跨文件不同 DOI 227 个；既无 DOI 也无 arXiv ID 的 10 条，合并时标 `UNVERIFIED`。
- OpenAlex `search=` 匹配全文：Q2–Q6 的前 25 条在标题+摘要层面多数不满足原检索式（词干还原后，有摘要者中满足 4/17、2/23、0/21、7/19、1/23）。对照试验中改用 `title_and_abstract.search` 后 Q6 为 22/25。是否切换由研究者决定。
- S2 bulk 只匹配标题+摘要，词干还原后符合度高（有摘要者 Q1 23/23、Q2 18/20、Q5 21/21、Q6 18/21）；Q3、Q4 命中少（9、1）。
- 本步未判断新颖性，未在日志中列出具体文献。

---

## [2026-10-31 14:58 UTC] Step 5 — OpenAlex 改为只匹配标题+摘要并重跑；合并去重

**研究者决定（本轮）**

- OpenAlex 改用 `filter=title_and_abstract.search`（只匹配标题+摘要，与 S2 bulk 一致），按 `relevance_score:desc` 取前 25 条。
- 重跑 OpenAlex 后合并去重。

**命令 1：修改 scripts/search.py**

```
# OpenAlex：search= 改为 filter=title_and_abstract.search:<检索式>，sort=relevance_score:desc
# 检索式含逗号时报错（filter 用逗号分隔条件）；meta.conversion / sort 相应更新
```

**命令 2：只重跑 OpenAlex（S2 保留 Step 4 的 bulk 结果）**

```bash
python3 scripts/search.py --sources openalex
```

输出：

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex               795    25     0  results/raw/openalex_Q1.json
Q2    component   openalex                38    25     0  results/raw/openalex_Q2.json
Q3    application openalex                 8     8     1  results/raw/openalex_Q3.json
Q4    application openalex                 1     1     0  results/raw/openalex_Q4.json
Q5    method      openalex                50    25     0  results/raw/openalex_Q5.json
Q6    concurrent  openalex                64    25     1  results/raw/openalex_Q6.json  [year>=2023]

6/6 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25: OpenAlex by relevance, S2 by citation count); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
exit code: 0
```

OpenAlex 对 6 条检索式的解析（meta.api_interpretation）均以 "in the title or abstract" 结尾。

**命令 3：质量检查（12 个文件；符合度用 Porter 词干还原，python3 内联脚本）**

```
file                  n  doi arXiv neither abstract  conform(stemmed, all)  conform(with abstract)
openalex_Q1           25   25     4       0       19            25/25                19/19
openalex_Q2           25   25     1       0       16            16/25                16/16
openalex_Q3            8    7     0       1        7             7/8                  7/7
openalex_Q4            1    1     0       0        0             0/1                  0/0
openalex_Q5           25   25     2       0       21            21/25                21/21
openalex_Q6           25   24     2       1       23            22/25                22/23
semantic_Q1           25   24    16       0       23            24/25                23/23
semantic_Q2           25   25     1       0       20            18/25                18/20
semantic_Q3            9    9     0       0        7             4/9                  4/7
semantic_Q4            1    1     0       0        0             0/1                  0/0
semantic_Q5           25   23     2       1       21            22/25                21/21
semantic_Q6           23   22     3       1       21            18/23                18/21
```

**命令 4：编写 scripts/merge.py，用合成记录单元测试（占位 ID，不进 results/）**

```bash
python3 -I -B - <<'PY'   # 内联测试：DOI 大小写、arXiv 版本、标题合并、短标题不合并、只有 arXiv DOI、两个期刊 DOI
PY
```

结果：ALL PASSED（11 条合成记录 → 7 组）。

**命令 5：第一次合并**

```bash
python3 scripts/merge.py
```

输出：

```
inputs:    12 files, 217 raw records
merged:    163 works (duplicates removed: 54; groups linked by title only: 8)
id_status: DOI 145 | arXiv 14 | UNVERIFIED 4
sources:   openalex only 56 | semanticscholar only 65 | both 42
per query: Q1 39 | Q2 35 | Q3 12 | Q4 1 | Q5 38 | Q6 38   (works hit by more than one query: 0)
written:   results/merged/merged.json
exit code: 0
```

完整性检查通过（217 条原始记录各出现一次；所有标识符都能回溯到原始记录）。人工核对 8 个只靠标题合并的组：7 组是同一研究的预印本与正式发表版本；M043 是 IEEE DataPort 数据集记录（DOI 前缀 10.21227）与同名 TechRxiv 预印本。另发现漏合并：同一 OSF 预印本（10.31234/osf.io/8p9wu）的不同版本 DOI（_v1…_v4）且标题措辞不同，被分成了两篇。

**命令 6：补充规则——预印本平台（OSF / TechRxiv / Research Square）的版本后缀 _vN、/vN 视为同一预印本；单元测试后重跑合并**

```bash
python3 -I -B - <<'PY'   # doi_key 与 OSF 版本合并测试：ALL PASSED
PY
python3 scripts/merge.py
python3 -I - <<'PY'      # 完整性检查 + 列出版本规则新合并的组
PY
```

输出：

```
inputs:    12 files, 217 raw records
merged:    161 works (duplicates removed: 56; groups linked by title only: 7)
id_status: DOI 143 | arXiv 14 | UNVERIFIED 4
sources:   openalex only 54 | semanticscholar only 65 | both 42
per query: Q1 37 | Q2 35 | Q3 12 | Q4 1 | Q5 38 | Q6 38   (works hit by more than one query: 0)
written:   results/merged/merged.json
exit code: 0
integrity: OK (217 raw refs each appear exactly once; all identifiers trace to raw records)
title_linked: ['M019(10.1016/j.tics.2026.01.003)', 'M023(10.1177/00491241251327130)', 'M025(10.1016/j.chbah.2025.100207)', 'M028(10.1108/xjm-01-2024-0015)', 'M043(10.21227/1051-8s48)', 'M067(10.2139/ssrn.6169367)', 'M071(10.31235/osf.io/dncuf_v1)']
UNVERIFIED:   ['M064<-openalex_Q6#10', 'M087<-openalex_Q3#1', 'M142<-semanticscholar_Q6#23', 'M161<-semanticscholar_Q5#13']
OSF 8p9wu now in 1 merged record(s): [('M025', 7)]
```

版本规则合并的两组均核对无误：M023（OSF 4esdp 与 4esdp_v2，早期版本标题措辞不同）、M025（OSF 8p9wu 的 5 个版本 DOI 与期刊版本）。

**产出文件**

- `results/raw/openalex_Q1.json` … `openalex_Q6.json` — 重跑覆盖：25 / 25 / 8 / 1 / 25 / 25 条
- `results/merged/merged.json` — 161 篇（由 217 条原始记录去重）
- `scripts/search.py` — 修改（命令 1）
- `scripts/merge.py` — 新增

**备注**

- id_status：DOI 143、arXiv 14、UNVERIFIED 4（M064、M087、M142、M161，原始记录中既无 DOI 也无 arXiv ID）。
- 只靠标题合并的 7 组带 `title_linked: true`。其中 M043 的主 DOI 是数据集（10.21227/1051-8s48），同组预印本为 10.36227/techrxiv.177223104.47525491/v1，建议人工核对。
- M028 的 alt_ids 中有一个 OpenAlex 原样返回的异常 DOI 字符串（带 "/full/html?utm_source=repec…" 后缀），按"不改写"原则保留。
- 来源：仅 OpenAlex 54、仅 S2 65、两者都有 42。没有一篇同时被两条以上检索式命中。
- 本步未判断新颖性，日志中未列出文献标题。

---

## [2026-10-31 15:08 UTC] Step 6 — merge.py 增加命中统计，输出前 20 候选 candidates.csv

**研究者要求（本轮）**：合并 results/raw 全部文件，按 DOI / arXiv ID / 规范化标题去重，统计每篇被多少条检索式、多少个来源命中，按命中次数降序取前 20 写到 `results/merged/candidates.csv`。

`scripts/merge.py` 在 Step 5 已建立（去重规则不变），本步在其上扩展。统计口径：

- `n_queries` 命中的检索式数；`n_sources` 命中的来源数
- `hits` 命中次数 = 命中的"检索式 × 来源"结果列表数（最多 12）；同一列表中同一篇的多个版本只算一次
- `mean_rank` 在各命中列表中最好名次的平均值（OpenAlex 名次按相关度，S2 名次按被引次数）
- 排序：hits 降序 → n_queries 降序 → n_sources 降序 → mean_rank 升序 → merged_id；取前 20

**命令 1：保存改动前的编号对照（用于确认编号不变）**

```bash
python3 -I -c "...json.dump({merged_id: raw_refs})..."   # -> 临时目录 merged_ids_before.json（161 条）
```

**命令 2：扩展 scripts/merge.py；单元测试（合成记录，占位 ID）**

```bash
python3 -I -B - <<'PY'   # 去重回归测试 + 命中统计 + 排序规则
PY
```

结果：regression (dedup) PASSED；hit statistics PASSED；candidate ordering PASSED。

**命令 3：运行**

```bash
python3 scripts/merge.py
```

输出：

```
inputs:     12 files, 217 raw records
merged:     161 works (duplicates removed: 56; groups linked by title only: 7)
id_status:  DOI 143 | arXiv 14 | UNVERIFIED 4
sources:    openalex only 54 | semanticscholar only 65 | both 42
per query:  Q1 37 | Q2 35 | Q3 12 | Q4 1 | Q5 38 | Q6 38   (works hit by more than one query: 0)
hits:       2 hit(s): 42 works | 1 hit(s): 119 works   (hits = number of query x source result lists containing the work)
written:    results/merged/merged.json, results/merged/candidates.csv (top 20)
cutoff:     #20 has hits=2; 42 works have hits=2, 22 of them fall outside the top 20 (decided by n_queries, n_sources, mean_rank)
candidates per query: Q1 4 | Q2 5 | Q3 5 | Q4 1 | Q5 2 | Q6 3

rank  id    hits  nq  ns mean_rank  identifier                                 title
   1  M010     2   1   2       1.0  doi:10.1038/s41586-025-09640-5             A multimodal robotic platform for multi-element electrocatal…
   2  M031     2   1   2       1.0  doi:10.1126/sciadv.adn5290                 Generative AI enhances individual creativity but reduces the…
   3  M039     2   1   2       1.0  doi:10.1016/j.ecolmodel.2018.04.020        Bibliometric review of ecological network analysis: 2010–201…
   4  M024     2   1   2       2.0  doi:10.1145/3635636.3656204                Homogenization Effects of Large Language Models on Human Cre…
   5  M022     2   1   2       2.5  doi:10.1016/j.caeai.2025.100456            Unveiling the dynamics of generative AI adoption: A business…
   6  M035     2   1   2       2.5  doi:10.1108/ijssp-06-2021-0145             Work–life balance: a systematic literature review and biblio…
   7  M036     2   1   2       2.5  doi:10.1080/08911762.2020.1765444          A Systematic Literature Review and Bibliometric Analysis of …
   8  M042     2   1   2       3.0  doi:10.1109/hicss.1993.270676              Drug design using inductive logic programming
   9  M002     2   1   2       3.5  doi:10.1038/s41598-026-54348-9             A temporal adaptive dictionary-constrained LDA and Bi-calibr…
  10  M032     2   1   2       3.5  doi:10.18559/ebr.2023.2.732                The rise of generative AI and possible effects on the econom…
  11  M040     2   1   2       4.0  doi:10.1186/s13643-018-0709-6              Evaluating characteristics of PROSPERO records as predictors…
  12  M037     2   1   2       4.5  doi:10.1007/978-981-15-1420-3_90           Feature Selection Algorithms in Medical Data Classification:…
  13  M019     2   1   2       5.0  doi:10.1016/j.tics.2026.01.003             The homogenizing effect of large language models on human ex…
  14  M034     2   1   2       5.5  doi:10.1007/s13132-022-00920-3             Design Thinking: from Bibliometric Analysis to Content Analy…
  15  M011     2   1   2       6.5  doi:10.48550/arxiv.2506.21818              A systematic review of research on large language models for…
  16  M026     2   1   2       6.5  doi:10.1109/access.2024.3491373            Optimizing Secure AI Lifecycle Model Management With Innovat…
  17  M005     2   1   2       7.0  doi:10.1177/01655515261461741              From connectivity to insight: A graph neural network–large l…
  18  M038     2   1   2       8.5  doi:10.1108/bij-04-2020-0137               Service supply chain: from bibliometric analysis to content …
  19  M009     2   1   2       9.0  doi:10.48550/arxiv.2606.10587              Towards Diverse Scientific Hypothesis Search with Large Lang…
  20  M025     2   1   2       9.0  doi:10.1016/j.chbah.2025.100207            Homogenizing effect of large language models (LLMs) on creat…
exit code: 0
```

**命令 4：核对与诊断（python3 内联脚本）**

```
# 编号对照、CSV 读回检查；按研究者的生成式 AI 筛选关键词统计（标题+摘要，正则，不区分大小写）：
# LLM(s) | ChatGPT | GPT-<数字> | Gemini | Claude | OpenAI | Anthropic | generative AI |
# generative artificial intelligence | large language model(s)
```

输出：

```
merged_id unchanged vs previous run: True
candidates.csv: BOM=True  rows=20  columns=17
ranks 1..20, hits non-increasing, id_status consistent: OK

top-20 mentioning generative-AI keywords in title/abstract: 11/20  ranks=[2, 4, 5, 9, 10, 13, 15, 16, 17, 19, 20]
top-20 published before 2023: 8/20
all 161 merged works mentioning these keywords: 112
```

**产出文件**

- `scripts/merge.py` — 扩展：命中统计、candidates.csv
- `results/merged/merged.json` — 重新生成（merged_id 与 Step 5 一致；每篇新增 n_queries / n_sources / hits / mean_rank；meta 新增 candidates 小节）
- `results/merged/candidates.csv` — 前 20 篇，17 列，带 BOM 的 UTF-8

**备注**

- 没有一篇被两条以上检索式命中，hits 只有 1 或 2（2 = 两个来源都命中同一检索式）。hits=2 的 42 篇并列，前 20 由并列规则（实际是 mean_rank）从中选出，另 22 篇落在前 20 之外。
- 前 20 按检索式分布：Q1 4、Q2 5、Q3 5、Q4 1、Q5 2、Q6 3。
- 前 20 中标题或摘要提到生成式 AI 关键词的有 11 篇，2023 年以前发表的 8 篇；全部 161 篇中提到这些关键词的有 112 篇。
- 本步未判断新颖性；日志中列出的文献均附 DOI。

---

## [2026-10-31 15:22 UTC] Step 7 — 证据表（前 10 篇）与 DOI 核验脚本

**研究者要求（本轮）**

1. 读 `candidates.csv` 前 10 篇的摘要，对照 `facets/facets.md` 逐面标 overlap / differ / unknown，写到 `evidence/evidence_table.md`（列：rank, 作者, 年份, 题目, DOI/arXiv, 五个面, verified）。
2. 写 `scripts/verify.py`：对每条 DOI 请求 `https://doi.org/<doi>`（跟随跳转），把 HTTP 状态和返回页标题写回 verified 列；没有 DOI 的标 UNVERIFIED。运行并记日志。

**命令 1：读取前 10 篇（python3 内联脚本，读 candidates.csv 前 10 行全部字段）**

结果：10 篇均有 DOI；9 篇有摘要，rank 1（M010）两个来源都没有返回摘要。

**命令 2：doi.org 连通性**

```bash
curl -sS -m 30 -o /dev/null -w "doi.org: HTTP %{http_code}\n" "https://doi.org/10.1126/sciadv.adn5290"
```

输出：

```
curl: (56) CONNECT tunnel failed, response 403
doi.org: HTTP 000
```

**命令 3：补作者（search.py 保存的字段不含作者；按 DOI 查 OpenAlex）**

```bash
python3 -B scripts/authors.py --top 10
```

输出：

```
  1 M010  n_authors=24   title_matches=True  first=Zhen Zhang  
  2 M031  n_authors=2    title_matches=True  first=Anil Rajnikant Doshi  
  3 M039  n_authors=4    title_matches=True  first=Stuart R. Borrett  
  4 M024  n_authors=3    title_matches=True  first=Barrett R. Anderson  
  5 M022  n_authors=6    title_matches=True  first=Hanadi Aldreabi  
  6 M035  n_authors=2    title_matches=True  first=Kumari Rashmi  
  7 M036  n_authors=3    title_matches=True  first=Payal R. Phulwani  
  8 M042  n_authors=6    title_matches=True  first=Ross D. King  
  9 M002  n_authors=1    title_matches=True  first=Xueqi Yin  
 10 M032  n_authors=2    title_matches=True  first=T. Orchard  
written: evidence/authors.json
exit code: 0
```

**命令 4：写 evidence/evidence_table.md**

逐篇阅读摘要，按文件中写明的标注规则逐面标注，并在"判定依据"一节附摘要原文。标签统计（python3 内联脚本解析表格）：

```
rows: 10; every row has 11 cells: True
研究问题: overlap 0 [] | differ 10 | unknown 0 []
作用机制: overlap 2 ['2', '4'] | differ 7 | unknown 1 ['1']
研究情境: overlap 0 [] | differ 9 | unknown 1 ['1']
数据与方法: overlap 5 ['3', '5', '6', '7', '9'] | differ 5 | unknown 0 []
预期发现: overlap 2 ['2', '4'] | differ 7 | unknown 1 ['1']
```

**命令 5：verify.py 本地测试（127.0.0.1 测试服务器，不访问外网）**

```bash
python3 -I -B - <<'PY'   # 正常跳转+标题（含 | 转义）、出版商 403、跳转后连接失败、仅 arXiv 无 DOI、页面无 <title>
PY
```

结果：ALL PASSED。

**命令 6：真实运行**

```bash
python3 -B scripts/verify.py
```

输出：

```
verify run at 2026-10-31T15:21:14+00:00  table=/home/user/novelty-probe-demo/evidence/evidence_table.md
[1] doi:10.1038/s41586-025-09640-5
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[2] doi:10.1126/sciadv.adn5290
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[3] doi:10.1016/j.ecolmodel.2018.04.020
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[4] doi:10.1145/3635636.3656204
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[5] doi:10.1016/j.caeai.2025.100456
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[6] doi:10.1108/ijssp-06-2021-0145
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[7] doi:10.1080/08911762.2020.1765444
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[8] doi:10.1109/hicss.1993.270676
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[9] doi:10.1038/s41598-026-54348-9
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)
[10] doi:10.18559/ebr.2023.2.732
      redirects: (no redirect)
      result:    BLOCKED at doi.org (network policy, proxy 403)

summary: BLOCKED at doi.org: 10
written: verified column in /home/user/novelty-probe-demo/evidence/evidence_table.md
exit code: 1
```

**产出文件**

- `scripts/authors.py` — 新增：按 DOI 从 OpenAlex 查作者
- `evidence/authors.json` — 前 10 篇的作者（OpenAlex 返回题目与表中题目 10/10 一致）
- `evidence/evidence_table.md` — 证据表与判定依据；verified 列目前为 BLOCKED
- `scripts/verify.py` — 新增：DOI 核验，结果写回 verified 列
- 删除 `evidence/.gitkeep`（目录已有文件）

**备注**

- `doi.org` 被本环境的网络策略拒绝（代理 403），10 个 DOI 均未能核验。需要研究者在环境设置中放行 `doi.org`；跟随跳转还会访问各出版商网站，这些域名也需放行或调宽网络访问级别。放行后重跑命令 6 即可覆盖 verified 列。
- 标注只依据摘要；rank 1 无摘要，仅研究问题与数据与方法两面依据题目标注，其余为 unknown。
- 本步未判断新颖性。

---

## [2026-10-31 15:37 UTC] Step 8 — 放行 doi.org / api.crossref.org，verify.py 增加 Crossref 元数据核验并重跑

**研究者决定（本轮）**

- 已在 Network Access 中放行 `doi.org` 与 `api.crossref.org`。
- 同意增加 Crossref 元数据核验（经 doi.org 内容协商取登记元数据），重跑 verify.py。

**命令 1：连通性与接口测试**

```bash
curl -sS -m 30 -o /dev/null -w "HTTP %{http_code} -> %{redirect_url}\n" "https://doi.org/10.1126/sciadv.adn5290"
curl -sS -m 30 -L -o /dev/null -w "HTTP %{http_code} final=%{url_effective}\n" "https://doi.org/10.1126/sciadv.adn5290"
curl -sS -m 30 -L -H "Accept: application/vnd.citationstyles.csl+json" "https://doi.org/10.1126/sciadv.adn5290"
curl -sS -m 30 -D - "https://api.crossref.org/works/10.1126/sciadv.adn5290"     # 以及间隔重试
```

输出（摘要）：

```
doi.org: HTTP 302 -> https://www.science.org/doi/10.1126/sciadv.adn5290
landing: curl: (56) CONNECT tunnel failed, response 403   (www.science.org 未放行)
Crossref（内容协商与 REST 接口）: HTTP 429，无 Retry-After、无响应体
间隔重试：15:33:11 try 1: HTTP 200
内容协商再试：HTTP 200 final=https://api.crossref.org/v1/works/10.1126%2Fsciadv.adn5290/transform
              type=application/vnd.citationstyles.csl+json；返回 title / container-title / issued / author 等字段
```

**命令 2：改写 scripts/verify.py**

```
# 每个 DOI 两项检查（均从 doi.org 出发并跟随跳转）：
#   Crossref：Accept: application/vnd.citationstyles.csl+json，取登记元数据，与表中题目对照；429/5xx 退避重试
#   落地页：Accept: text/html，记录 HTTP 状态与页面标题
# verified 列写成 "Crossref <结果>；落地页 <结果>"；同时更新 evidence_table.md 开头对 verified 列的说明
```

**命令 3：本地测试（127.0.0.1 测试服务器，按 Accept 头分别返回元数据或网页）**

结果：ALL PASSED（题目一致 / 不一致、Crossref 两次 429 后成功、DOI 不存在、元数据请求返回 HTML、出版商 403、跳转后连接失败、无 DOI）。

**命令 4：第一次真实运行**

```bash
python3 -B scripts/verify.py
```

输出：

```
verify run at 2026-10-31T15:35:22+00:00  table=/home/user/novelty-probe-demo/evidence/evidence_table.md
[1] doi:10.1038/s41586-025-09640-5
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · A multimodal robotic platform for multi-element electrocatalyst discovery
                 registered: Nature | 2025 | journal-article | authors: Zhang; Ren; Hsu
      landing:   302 www.nature.com  -> 落地页 BLOCKED at www.nature.com (network policy, proxy 403)
[2] doi:10.1126/sciadv.adn5290
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the collective diversity of novel content
                 registered: Science Advances | 2024 | journal-article | authors: Doshi; Hauser
      landing:   302 www.science.org  -> 落地页 BLOCKED at www.science.org (network policy, proxy 403)
[3] doi:10.1016/j.ecolmodel.2018.04.020
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Bibliometric review of ecological network analysis: 2010–2016
                 registered: Ecological Modelling | 2018 | journal-article | authors: Borrett; Sheble; Moody
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[4] doi:10.1145/3635636.3656204
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Homogenization Effects of Large Language Models on Human Creative Ideation
                 registered: Creativity and Cognition | 2024 | proceedings-article | authors: Anderson; Shah; Kreminski
      landing:   302 dl.acm.org  -> 落地页 BLOCKED at dl.acm.org (network policy, proxy 403)
[5] doi:10.1016/j.caeai.2025.100456
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Unveiling the dynamics of generative AI adoption: A business intelligence analysis through topic modeling-based bibliome…
                 registered: Computers and Education: Artificial Intelligence | 2025 | journal-article | authors: Aldreabi; Alhur; Al-Okaily
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[6] doi:10.1108/ijssp-06-2021-0145
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Work–life balance: a systematic literature review and bibliometric analysis
                 registered: International Journal of Sociology and Social Policy | 2021 | journal-article | authors: Rashmi; Kataria
      landing:   302 www.emerald.com  -> 落地页 ERROR at www.emerald.com: [Errno -2] Name or service not known
[7] doi:10.1080/08911762.2020.1765444
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · A Systematic Literature Review and Bibliometric Analysis of Recycling Behavior
                 registered: Journal of Global Marketing | 2020 | journal-article | authors: Phulwani; Kumar; Goyal
      landing:   302 www.tandfonline.com  -> 落地页 BLOCKED at www.tandfonline.com (network policy, proxy 403)
[8] doi:10.1109/hicss.1993.270676
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Drug design using inductive logic programming
                 registered: [1993] Proceedings of the Twenty-sixth Hawaii International Conference on System Sciences | None | proceedings-article | authors: King; Srinivasan; Muggleton
      landing:   302 ieeexplore.ieee.org  -> 落地页 ERROR at ieeexplore.ieee.org: [Errno -2] Name or service not known
[9] doi:10.1038/s41598-026-54348-9
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目不一致 · A temporal adaptive dictionary-constrained LDA and Bi-calibrated dual granularity DTM framework for dynamic topic evolut…
                 registered: Scientific Reports | 2026 | journal-article | authors: Yin
      landing:   302 www.nature.com  -> 落地页 BLOCKED at www.nature.com (network policy, proxy 403)
[10] doi:10.18559/ebr.2023.2.732
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · The rise of generative AI and possible effects on the economy
                 registered: Economics and Business Review | 2023 | journal-article | authors: Orchard; Tasiemski
      landing:   302 journals.ue.poznan.pl  -> 落地页 BLOCKED at journals.ue.poznan.pl (network policy, proxy 403)

summary crossref: 题目一致: 9 | 题目不一致: 1
summary landing:  落地页 BLOCKED at dl.acm.org: 1 | 落地页 BLOCKED at journals.ue.poznan.pl: 1 | 落地页 BLOCKED at linkinghub.elsevier.com: 2 | 落地页 BLOCKED at www.nature.com: 2 | 落地页 BLOCKED at www.science.org: 1 | 落地页 BLOCKED at www.tandfonline.com: 1 | 落地页 ERROR at ieeexplore.ieee.org: [Errno -2] Name or service not known: 1 | 落地页 ERROR at www.emerald.com: [Errno -2] Name or service not known: 1
written: verified column in /home/user/novelty-probe-demo/evidence/evidence_table.md
exit code: 0
```

核对输出时发现两处问题：

1. rank 9 的"题目不一致"是脚本 bug：比对前先把登记题目截短到 120 字符，长题目结尾的词被截掉，导致词重合率低于八成。
2. emerald.com 与 ieeexplore.ieee.org 报的是域名解析失败。查看跳转链确认：doi.org 把这两个 DOI 转到了 `http://` 地址，而本环境只经代理访问 HTTPS。

```
10.1108/ijssp-06-2021-0145 | chain: [(302, 'http://www.emerald.com/ijssp/article/42/11-12/1028-1065/159262')] | error: [Errno -2] Name or service not known
10.1109/hicss.1993.270676 | chain: [(302, 'http://ieeexplore.ieee.org/document/270676/')] | error: [Errno -2] Name or service not known
```

**命令 5：修正并回归测试**

```
# 比对用完整登记题目，只在写入表格时截短；非 HTTPS 地址的失败信息带上 http:// 前缀
python3 -I -B - <<'PY'   # 回归测试：长题目判为一致；跳到 http:// 地址时信息带前缀 —— PASSED
PY
```

**命令 6：第二次真实运行**

```bash
python3 -B scripts/verify.py
```

输出：

```
verify run at 2026-10-31T15:36:54+00:00  table=/home/user/novelty-probe-demo/evidence/evidence_table.md
[1] doi:10.1038/s41586-025-09640-5
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · A multimodal robotic platform for multi-element electrocatalyst discovery
                 registered: Nature | 2025 | journal-article | authors: Zhang; Ren; Hsu
      landing:   302 www.nature.com  -> 落地页 BLOCKED at www.nature.com (network policy, proxy 403)
[2] doi:10.1126/sciadv.adn5290
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the collective diversity of novel content
                 registered: Science Advances | 2024 | journal-article | authors: Doshi; Hauser
      landing:   302 www.science.org  -> 落地页 BLOCKED at www.science.org (network policy, proxy 403)
[3] doi:10.1016/j.ecolmodel.2018.04.020
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Bibliometric review of ecological network analysis: 2010–2016
                 registered: Ecological Modelling | 2018 | journal-article | authors: Borrett; Sheble; Moody
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[4] doi:10.1145/3635636.3656204
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Homogenization Effects of Large Language Models on Human Creative Ideation
                 registered: Creativity and Cognition | 2024 | proceedings-article | authors: Anderson; Shah; Kreminski
      landing:   302 dl.acm.org  -> 落地页 BLOCKED at dl.acm.org (network policy, proxy 403)
[5] doi:10.1016/j.caeai.2025.100456
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Unveiling the dynamics of generative AI adoption: A business intelligence analysis through topic modeling-based bibliome…
                 registered: Computers and Education: Artificial Intelligence | 2025 | journal-article | authors: Aldreabi; Alhur; Al-Okaily
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[6] doi:10.1108/ijssp-06-2021-0145
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Work–life balance: a systematic literature review and bibliometric analysis
                 registered: International Journal of Sociology and Social Policy | 2021 | journal-article | authors: Rashmi; Kataria
      landing:   302 www.emerald.com  -> 落地页 ERROR at http://www.emerald.com: [Errno -2] Name or service not known
[7] doi:10.1080/08911762.2020.1765444
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · A Systematic Literature Review and Bibliometric Analysis of Recycling Behavior
                 registered: Journal of Global Marketing | 2020 | journal-article | authors: Phulwani; Kumar; Goyal
      landing:   302 www.tandfonline.com  -> 落地页 BLOCKED at www.tandfonline.com (network policy, proxy 403)
[8] doi:10.1109/hicss.1993.270676
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Drug design using inductive logic programming
                 registered: [1993] Proceedings of the Twenty-sixth Hawaii International Conference on System Sciences | None | proceedings-article | authors: King; Srinivasan; Muggleton
      landing:   302 ieeexplore.ieee.org  -> 落地页 ERROR at http://ieeexplore.ieee.org: [Errno -2] Name or service not known
[9] doi:10.1038/s41598-026-54348-9
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · A temporal adaptive dictionary-constrained LDA and Bi-calibrated dual granularity DTM framework for dynamic topic evolut…
                 registered: Scientific Reports | 2026 | journal-article | authors: Yin
      landing:   302 www.nature.com  -> 落地页 BLOCKED at www.nature.com (network policy, proxy 403)
[10] doi:10.18559/ebr.2023.2.732
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · The rise of generative AI and possible effects on the economy
                 registered: Economics and Business Review | 2023 | journal-article | authors: Orchard; Tasiemski
      landing:   302 journals.ue.poznan.pl  -> 落地页 BLOCKED at journals.ue.poznan.pl (network policy, proxy 403)

summary crossref: 题目一致: 10
summary landing:  落地页 BLOCKED at dl.acm.org: 1 | 落地页 BLOCKED at journals.ue.poznan.pl: 1 | 落地页 BLOCKED at linkinghub.elsevier.com: 2 | 落地页 BLOCKED at www.nature.com: 2 | 落地页 BLOCKED at www.science.org: 1 | 落地页 BLOCKED at www.tandfonline.com: 1 | 落地页 ERROR at http://ieeexplore.ieee.org: [Errno -2] Name or service not known: 1 | 落地页 ERROR at http://www.emerald.com: [Errno -2] Name or service not known: 1
written: verified column in /home/user/novelty-probe-demo/evidence/evidence_table.md
exit code: 0
```

**产出文件**

- `scripts/verify.py` — 改写：Crossref 元数据核验 + 落地页检查
- `evidence/evidence_table.md` — verified 列已更新；开头补充 verified 列的格式说明

**备注**

- Crossref：10/10 返回 200，登记题目与表中题目全部一致；登记的期刊、年份、作者见上方输出。
- 落地页：10 个 DOI 都解析到了出版商页面，但页面本身未能访问。8 个出版商 HTTPS 域名未放行（www.nature.com、www.science.org、linkinghub.elsevier.com、dl.acm.org、www.tandfonline.com、journals.ue.poznan.pl）；2 个 DOI 登记的是 `http://` 地址（www.emerald.com、ieeexplore.ieee.org），本环境无法访问。
- 第一次运行中 rank 9 的"题目不一致"由脚本 bug 造成，已修正并重跑；以第二次运行结果为准。
- 本步未判断新颖性。

---

## [2026-10-31 15:46 UTC] Step 9 — 生成差异陈述模板（未填写）

**研究者要求（本轮）**：生成 `evidence/difference_statement.md` 模板，只留空白：最接近的三篇（从证据表复制）；本想法在哪一个面上不同、差多大（人填）；审稿人最可能说"已被做过"的一条理由及其文献（人填）。不要代为填写。

**命令 1：写入模板**

```
# 写入 evidence/difference_statement.md：三节均为空白
# 第 1 节为空表，列与 evidence_table.md 相同，三行留空，由研究者从证据表复制整行（选哪三篇由研究者决定）
```

**命令 2：检查模板（python3 内联脚本）**

```
header identical to evidence_table.md: True (11 columns)
blank rows: 3 | all cells empty: True | cell counts: [11, 11, 11]
fill-in fields: 5 | all end with '：' (nothing filled): True
```

**产出文件**

- `evidence/difference_statement.md` — 差异陈述模板（未填写任何内容）

**备注**：本步未选择文献、未填写内容、未判断新颖性。

---

## [2026-10-31 15:52 UTC] Step 10 — 差异陈述第 1 节：从证据表选出并复制最接近的三篇

**研究者要求（本轮）**：第 1 节"最接近的三篇（从证据表复制）"由检索助手完成；第 2、3 节仍由研究者填写。

**命令 1：按证据表标注排序并检查并列（python3 内联脚本）**

```
step 1 — overlap count per row:
  rank  2: 2 overlap ['作用机制', '预期发现']
  rank  4: 2 overlap ['作用机制', '预期发现']
  rank  3: 1 overlap ['数据与方法']
  rank  5: 1 overlap ['数据与方法']
  rank  6: 1 overlap ['数据与方法']
  rank  7: 1 overlap ['数据与方法']
  rank  9: 1 overlap ['数据与方法']
  rank  1: 0 overlap []
  rank  8: 0 overlap []
  rank 10: 0 overlap []

step 2 — top by overlap count: ranks ['2', '4']; third slot tied at 1 overlap: ranks ['3', '5', '6', '7', '9']
  rank  3: generative-AI keywords in title/abstract: none
  rank  5: generative-AI keywords in title/abstract: ['generative ai', 'generative artificial intelligence']
  rank  6: generative-AI keywords in title/abstract: none
  rank  7: generative-AI keywords in title/abstract: none
  rank  9: generative-AI keywords in title/abstract: ['generative ai', 'large language models']
```

选择规则（已写入 `evidence/difference_statement.md` 第 1 节表下）：

1. 按标为 overlap 的面数排序：rank 2、rank 4 各 2 个面，入选。
2. 第三篇在 rank 3、5、6、7、9 的并列中选出：先保留标题或摘要涉及生成式 AI 的（剩 rank 5、9）；再比较"数据与方法"面覆盖 facets.md 所列内容的多少。rank 9 的摘要写明数据为 WoS 2014–2023 年 AI 论文，并追踪主题随时间的变化；rank 5 未说明数据规模与时间跨度。取 rank 9。

**命令 2：更新说明文字；用脚本把 rank 2、4、9 三行原样复制进第 1 节的空表**

```
copied rows identical to evidence_table.md: [True, True, True]
rows copied: ['2', '4', '9']
sections 2-3 fields still blank: True (5 fields)
```

**产出文件**

- `evidence/difference_statement.md` — 第 1 节已填（rank 2、4、9，附选择规则）；第 2、3 节仍为空白

**备注**："最接近"只表示在证据表中的相对位置，依据是证据表的标注与摘要；本步未判断新颖性，未填写第 2、3 节。

---

## [2026-10-31 16:59 UTC] Step 11 — v2 准备：核验研究者给出的参考文献，诊断 v1 漏检，写 idea_v2.md

**研究者要求（本轮）**：把研究情境改为"管理学与经济学研究"，保存为 `idea/idea_v2.md`，用 v2 重跑 T2–T5，产出 `_v2` 文件。研究者告知：上一轮的标准答案是 Hao, Q., Xu, F., Li, Y. et al. Artificial intelligence tools expand scientists' impact but contract science's focus. Nature 649, 1237–1243 (2026). https://doi.org/10.1038/s41586-025-09922-y ；该论文明确排除了经济学和商科。

步骤对应：T2 = 拆面与检索式（Step 1），T3 = 检索（Step 2–4），T4 = 合并去重与候选（Step 5–6），T5 = 证据表与 DOI 核验（Step 7–8）。

**说明**：`idea/idea.md` 原文没有"自然科学"字样，情境是笼统的"科研人员 / 整个学科"（v1 的检索词如 AI for science、scientists 偏向自然科学）。`idea/idea.md` 保持不变。

**命令 1：核验参考文献并查 v1 结果（python3 内联脚本：verify.py 的 Crossref 检查、OpenAlex 与 S2 按 DOI 查询、OpenAlex 题目检索找其他版本、用预印本摘要逐条检验 v1 检索式）**

输出：

```
Crossref: Crossref HTTP 200 · 题目一致 · Artificial intelligence tools expand scientists’ impact but contract science’s focus
  registered: Nature | volume 649 | pages 1237-1243 | issued [[2026, 1, 14]] | authors: Hao; Xu; Li; Evans ...
OpenAlex: https://openalex.org/W7124140759 | 2026 | Artificial intelligence tools expand scientists’ impact but contract science’s focus
  abstract: (none)
in v1 raw results: NOT FOUND (0 of 217 records)
S2: Artificial intelligence tools expand scientists’ impact but contract science’s focus | 2026 | Nature | externalIds: {'DOI': '10.1038/s41586-025-09922-y', 'CorpusId': 284736867, 'PubMed': '41535462'}
  abstract: (none)
OpenAlex title search: title.search:scientists AND impact AND focus,from_publication_date:2024-01-01 | count: 4
  2026 | https://doi.org/10.1038/s41586-025-09922-y | Nature | abstract: no | Artificial intelligence tools expand scientists’ impact but contract science’s focus
  2026 | https://doi.org/10.1016/j.eururo.2026.04.004 | European Urology | abstract: no | Re: Artificial Intelligence Tools Expand Scientists’ Impact but Contract Science’s Focus
  2024 | https://doi.org/10.48550/arxiv.2412.07727 | arXiv (Cornell University) | abstract: yes | Artificial Intelligence Tools Expand Scientists' Impact but Contract Science's Focus (Just
  2026 | https://doi.org/10.1093/bjs/znag063.140 | British journal of surgery | abstract: yes | 917 Evaluating Ethical Readiness in Emerging Surgeon Scientists: Impact of an LMIC Focused
preprint: https://openalex.org/W4405273923 | 2024 | Artificial Intelligence Tools Expand Scientists' Impact but Contract Science's Focus (Just accepted by Nature, to be online soon)
abstract: Development in Artificial Intelligence (AI) has accelerated scientific discovery. Alongside recent AI-oriented Nobel prizes, these trends establish the role of AI tools in science. This advancement raises questions about the potential influences of AI tools on scientists and science as a whole, and highlights a potential conflict between individual and collective benefits. To evaluate, we used a pretrained language model to identify AI-augmented research, with an F1-score of 0.875 in validation against expert-labeled data. Using a dataset of 41.3 million research papers across natural science and covering distinct eras of AI, here we show an accelerated adoption of AI tools among scientists and consistent professional advantages associated with AI usage, but a collective narrowing of scientific focus. Scientists who engage in AI-augmented research publish 3.02 times more papers, receive 4.84 times more citations, and become research project leaders 1.37 years earlier than those who do not. By contrast, AI adoption shrinks the collective volume of scientific topics studied by 4.63% and decreases scientist's engagement with one another by 22.00%. Thereby, AI adoption in science presents a seeming paradox -- an expansion of individual scientists' impact but a contraction in collective science's reach -- as AI-augmented work moves collectively toward areas richest in data. With reduced follow-on engagement, AI tools appear to automate established fields rather than explore new ones, highlighting a tension between personal advancement and collective scientific progress.

v1 queries vs preprint title+abstract (stemmed; per AND group: matched terms):
  Q1 satisfied=False  groups=[[], []]
  Q2 satisfied=False  groups=[[], []]
  Q3 satisfied=False  groups=[[], []]
  Q4 satisfied=False  groups=[[], [], ['scientist*']]
  Q5 satisfied=False  groups=[[], [], []]
  Q6 satisfied=False  groups=[[], [], ['scientist*']]
```

结论：

- DOI 有效，Crossref 登记题目一致（Nature 649: 1237–1243，2026-01-14）。
- v1 的 217 条原始记录中没有它。Nature 版在 OpenAlex 与 S2 都没有摘要，只能靠题目匹配。
- 同一研究的 arXiv 预印本（doi:10.48550/arxiv.2412.07727）有摘要，但不满足 v1 任何一条检索式：AI 一侧用的是 "Artificial Intelligence (AI)"、"AI tools"，结果一侧用的是 "narrowing of scientific focus"、"shrinks the collective volume of scientific topics"，v1 的检索词都匹配不到。
- 预印本摘要写明数据为 "41.3 million research papers across natural science"。"明确排除经济学和商科"在摘要中未提及，记为研究者提供的信息。

**命令 2：写入 idea/idea_v2.md（只改情境）**

```
v1：我注意到身边越来越多人用 AI 做研究。我想研究：科研人员使用 AI 工具，会不会让整个学科的选题变窄？打算用大规模论文数据来测。
v2：我注意到身边越来越多人用 AI 做研究。我想研究：管理学与经济学领域的研究者使用 AI 工具，会不会让这两个学科的选题变窄？打算用大规模论文数据来测。
```

**产出文件**：`idea/idea_v2.md`


---

## [2026-10-31 16:59 UTC] Step 12 — T2 v2：拆面与检索式

**命令 1：写入 facets/facets_v2.md、queries/queries_v2.json**

与 v1 的差异及原因写在 `facets/facets_v2.md` 的"与 v1 的差异及原因"一节：情境词改为管理学与经济学（研究者要求）；按 Step 11 的诊断加入 "AI tools"、"artificial intelligence"，并把 "narrowing of science" 放宽为 narrowing；去掉自然科学取向的词与 v1 中带来误命中的词。沿用研究者决定：AI 工具只指生成式 AI（筛选时判断），concurrent 只取 2023 年起。

**命令 2：校验（python3 内联脚本，同 Step 1 的检查，另检验参考文献预印本满足哪些 v2 检索式）**

```
research_question  5 terms: ['AI tools', 'artificial intelligence', 'generative AI', 'large language models', 'research topic selection']
mechanism          5 terms: ['homogenization', 'algorithmic monoculture', 'streetlight effect', 'exploration-exploitation', 'Matthew effect']
context            5 terms: ['economists', 'economic research', 'management research', 'business research', 'scientists']
data_method        5 terms: ['science of science', 'bibliometrics', 'topic modeling', 'LLM-generated text', 'difference-in-differences']
expected_findings  5 terms: ['narrowing', 'topic diversity', 'topic concentration', 'collective diversity', 'research diversification']
Q1 component   OK  facets=['expected_findings', 'mechanism', 'research_question']
Q2 component   OK  facets=['context', 'expected_findings']
Q3 application OK  facets=['context', 'expected_findings', 'research_question']
Q4 application OK  facets=['context', 'mechanism', 'research_question']
Q5 method      OK  facets=['data_method', 'research_question']
Q6 concurrent  OK  facets=['context', 'expected_findings', 'research_question']
unused terms: none (25/25 used)

reference preprint (arXiv 2412.07727) vs v2 queries: {'Q1': False, 'Q2': False, 'Q3': True, 'Q4': False, 'Q5': False, 'Q6': False}
```

注意：v2 检索词是在知道 v1 漏检原因之后调整的，预印本满足 Q3 只说明修正生效，不是独立的召回验证。

**产出文件**：`facets/facets_v2.md`、`queries/queries_v2.json`

**备注**：本步未判断新颖性。

---

## [2026-10-31 16:59 UTC] Step 13 — T3 v2：脚本支持版本后缀；v2 检索

**命令 1：修改脚本（v1 默认行为不变）**

```
# scripts/search.py：新增 --queries、--suffix（输出 results/raw/{source}_{query_id}{suffix}.json）；
#                    meta 记录 queries_file；截断词表补充 economist* -> economists
# scripts/merge.py： 新增 --suffix，只读取后缀完全相同的文件（v1 与 v2 不会混在一起）；
#                    出处 raw_refs 带后缀；输出 merged{suffix}.json、candidates{suffix}.csv
# scripts/authors.py：新增 --candidates、--out
```

**命令 2：回归测试（确认 v1 结果可原样复现）**

```bash
python3 -I -B - <<'PY'   # 文件名匹配：v1 / v2 互不包含
PY
python3 -B scripts/merge.py   # 用修改后的脚本重跑 v1，与已提交版本逐项比较，比较后恢复原文件
```

输出：

```
suffix ''     matches: ['openalex_Q1.json', 'semanticscholar_Q6.json']
suffix '_v2'  matches: ['openalex_Q1_v2.json', 'semanticscholar_Q6_v2.json']
v1 raw files selected: 12 | records: 217
v1 re-run with modified merge.py: records identical=True | meta identical (except created_at)=True | candidates.csv identical=True
```

**命令 3：v2 检索**

```bash
python3 -B scripts/search.py --queries queries/queries_v2.json --suffix _v2
```

输出：

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex               782    25     0  results/raw/openalex_Q1_v2.json
Q1    component   semanticscholar        392    25     0  results/raw/semanticscholar_Q1_v2.json
Q2    component   openalex              2759    25     5  results/raw/openalex_Q2_v2.json
Q2    component   semanticscholar       2161    25     6  results/raw/semanticscholar_Q2_v2.json
Q3    application openalex               299    25     0  results/raw/openalex_Q3_v2.json
Q3    application semanticscholar        123    25     3  results/raw/semanticscholar_Q3_v2.json
Q4    application openalex                 3     3     0  results/raw/openalex_Q4_v2.json
Q4    application semanticscholar          0     0     0  results/raw/semanticscholar_Q4_v2.json
Q5    method      openalex                50    25     0  results/raw/openalex_Q5_v2.json
Q5    method      semanticscholar         45    25     1  results/raw/semanticscholar_Q5_v2.json
Q6    concurrent  openalex                42    25     1  results/raw/openalex_Q6_v2.json  [year>=2023]
Q6    concurrent  semanticscholar          7     7     0  results/raw/semanticscholar_Q6_v2.json  [year>=2023]

12/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25: OpenAlex by relevance, S2 by citation count); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
exit code: 0
```

**命令 4：质量检查（符合度用 Porter 词干还原；并查找参考文献）**

```
file                     n  doi arXiv neither abstract  conform(stemmed,all)  conform(with abstract)
openalex_Q1_v2          25   25     4       0       19          25/25                19/19
openalex_Q2_v2          25   20     0       5       20          22/25                20/20
openalex_Q3_v2          25   25     4       0       20          20/25                20/20
openalex_Q4_v2           3    3     0       0        3           3/3                  3/3
openalex_Q5_v2          25   25     2       0       21          21/25                21/21
openalex_Q6_v2          25   24     1       1       18          18/25                18/18
semantic_Q1_v2          25   24    16       0       23          24/25                23/23
semantic_Q2_v2          25   19     0       6        2           3/25                 2/2
semantic_Q3_v2          25   22     2       3       16          16/25                16/16
semantic_Q4_v2           0    0     0       0        0           0/0                  0/0
semantic_Q5_v2          25   23     2       1       21          22/25                21/21
semantic_Q6_v2           7    7     1       0        7           7/7                  7/7

reference paper (Hao et al.; Nature DOI or arXiv 2412.07727) in v2 raw results: ['openalex_Q3_v2#2 (doi=10.1038/s41586-025-09922-y, arXiv=None)', 'openalex_Q3_v2#5 (doi=10.48550/arxiv.2412.07727, arXiv=2412.07727)', 'semanticscholar_Q3_v2#1 (doi=10.1038/s41586-025-09922-y, arXiv=None)']
```

**产出文件**：`results/raw/openalex_Q1_v2.json` … `semanticscholar_Q6_v2.json`（12 个；S2 Q4 为 0 条）；`scripts/search.py`、`scripts/merge.py`、`scripts/authors.py`（修改）

**备注**：参考文献在 Q3 中被检索到（OpenAlex Nature 版第 2 名、预印本第 5 名；S2 Nature 版第 1 名）。本步未判断新颖性。

---

## [2026-10-31 16:59 UTC] Step 14 — T4 v2：合并去重与前 20 候选

**命令 1：合并 v2 结果**

```bash
python3 -B scripts/merge.py --suffix _v2
```

输出：

```
inputs:     12 files, 235 raw records
merged:     191 works (duplicates removed: 44; groups linked by title only: 7)
id_status:  DOI 160 | arXiv 16 | UNVERIFIED 15
sources:    openalex only 84 | semanticscholar only 76 | both 31
per query:  Q1 37 | Q2 47 | Q3 43 | Q4 3 | Q5 38 | Q6 24   (works hit by more than one query: 1)
hits:       2 hit(s): 32 works | 1 hit(s): 159 works   (hits = number of query x source result lists containing the work)
written:    results/merged/merged_v2.json, results/merged/candidates_v2.csv (top 20)
cutoff:     #20 has hits=2; 32 works have hits=2, 12 of them fall outside the top 20 (decided by n_queries, n_sources, mean_rank)
candidates per query: Q1 5 | Q2 2 | Q3 4 | Q4 0 | Q5 3 | Q6 7

rank  id    hits  nq  ns mean_rank  identifier                                 title
   1  M001     2   2   1       8.0  doi:10.2139/ssrn.4389118                   Artificial Intelligence and the Economics of Decision-Making
   2  M027     2   1   2       1.0  doi:10.1126/sciadv.adn5290                 Generative AI enhances individual creativity but reduces the…
   3  M003     2   1   2       1.5  doi:10.1038/s41586-025-09922-y             Artificial intelligence tools expand scientists’ impact but …
   4  M021     2   1   2       2.0  doi:10.1145/3635636.3656204                Homogenization Effects of Large Language Models on Human Cre…
   5  M018     2   1   2       2.5  doi:10.1016/j.caeai.2025.100456            Unveiling the dynamics of generative AI adoption: A business…
   6  M025     2   1   2       2.5  doi:10.1177/20563051231186353              Artificial Intelligence and Democracy: A Conceptual Framewor…
   7  M015     2   1   2       5.0  doi:10.47309/2713-2358-2025-4-184-195      Issues of using artificial intelligence in scientific resear…
   8  M016     2   1   2       5.5  doi:10.1016/j.tics.2026.01.003             The homogenizing effect of large language models on human ex…
   9  M012     2   1   2       6.5  doi:10.48550/arxiv.2506.21818              A systematic review of research on large language models for…
  10  M026     2   1   2       6.5  doi:10.3390/cancers15092573                Artificial Intelligence in CT and MR Imaging for Oncological…
  11  M004     2   1   2       7.0  doi:10.63313/ebm.9154                      Artificial Intelligence-Embedded Restructuring of Enterprise…
  12  M019     2   1   2       7.0  doi:10.6018/turismo.616471                 CYBERSECURITY IN TOURISM AND HOSPITALITY MANAGEMENT RESEARCH…
  13  M030     2   1   2       7.5  doi:10.5465/amj.2008.34789630              From the Editors Beyond Contextualization: Using Context The…
  14  M024     2   1   2       8.0  doi:10.48550/arxiv.2409.15626              Qualitative Insights Tool (QualIT): LLM Enhanced Topic Model…
  15  M031     2   1   2       8.5  doi:10.1111/1467-8551.12.s1.2              Bridging the Relevance Gap: Aligning Stakeholders in the Fut…
  16  M022     2   1   2       9.0  doi:10.1016/j.chbah.2025.100207            Homogenizing effect of large language models (LLMs) on creat…
  17  M008     2   1   2       9.5  doi:10.1007/s10462-026-11543-4             Mapping the landscape of AI-empowered psychology: a topic mo…
  18  M010     2   1   2      10.0  doi:10.1111/joes.70175                     Regulating the Artificial Intelligence Economy: A Systematic…
  19  M011     2   1   2      12.0  doi:10.3390/computers15100689              Toward AI-Enabled Process Model Selection for IT Projects: A…
  20  M020     2   1   2      12.5  doi:10.1177/00491241251327130              Generative AI Meets Open-Ended Survey Responses: Research Pa…
exit code: 0
```

**命令 2：定位参考文献（python3 内联脚本，按出处精确匹配）**

第一次定位用了前缀匹配（"#2" 误匹配到 "#20"–"#25"），输出有误，已改为精确匹配重查：

```
M003 | doi 10.1038/s41586-025-09922-y | arXiv None | hits 2 | refs ['openalex_Q3_v2#2', 'semanticscholar_Q3_v2#1'] | candidates_v2 rank: 3
M106 | doi 10.48550/arxiv.2412.07727 | arXiv 2412.07727 | hits 1 | refs ['openalex_Q3_v2#5'] | candidates_v2 rank: not in top 20
```

**产出文件**：`results/merged/merged_v2.json`（191 篇）、`results/merged/candidates_v2.csv`（前 20）

**备注**

- 参考文献的 Nature 版（M003）两个来源都命中，在 candidates_v2 中排第 3。同一研究的 arXiv 预印本（M106）单独成了一条：其题目多了 "(Just accepted by Nature, to be online soon)"，与正式版没有共同的 DOI 或 arXiv ID，现有去重规则没有把两者并在一起。
- UNVERIFIED 15 篇，多来自 S2 的 Q2（按被引次数排在前面的老文献缺少标识符）。
- hits 只有 1 或 2；hits=2 的 32 篇并列，前 20 由并列规则从中选出。
- 本步未判断新颖性。

---

## [2026-10-31 17:00 UTC] Step 15 — T5 v2：证据表与 DOI 核验

**命令 1：作者（按 DOI 查 OpenAlex）**

```bash
python3 -B scripts/authors.py --top 10 --candidates results/merged/candidates_v2.csv --out evidence/authors_v2.json
```

输出：

```
  1 M001  n_authors=1    title_matches=True  first=Wim A. Naudé  
  2 M027  n_authors=2    title_matches=True  first=Anil Rajnikant Doshi  
  3 M003  n_authors=4    title_matches=True  first=Qianyue Hao  
  4 M021  n_authors=3    title_matches=True  first=Barrett R. Anderson  
  5 M018  n_authors=6    title_matches=True  first=Hanadi Aldreabi  
  6 M025  n_authors=1    title_matches=True  first=Andreas Martin Jungherr  
  7 M015  n_authors=1    title_matches=True  first=Ильдар Узбекович Зулькарнай  
  8 M016  n_authors=3    title_matches=True  first=Zhivar Sourati  
  9 M012  n_authors=3    title_matches=True  first=Meina Zhu  
 10 M026  n_authors=13   title_matches=True  first=Ramesh Paudyal  
written: evidence/authors_v2.json
exit code: 0
```

**命令 2：读前 10 篇摘要；核对它们靠哪些结果词命中（python3 内联脚本，词干还原）**

```
top-10 of candidates_v2: which outcome-group terms (F5 + 'research topic selection') occur in title+abstract (stemmed)
  rank  1 M001 (queries Q3;Q6): ['narrowing -> "to narrow applications which"']
  rank  2 M027 (queries Q1): ['narrowing -> "a narrower scope of"', 'collective diversity -> "the collective diversity of novel"']
  rank  3 M003 (queries Q3): none in title/abstract
  rank  4 M021 (queries Q1): none in title/abstract
  rank  5 M018 (queries Q5): none in title/abstract
  rank  6 M025 (queries Q3): ['narrowing -> "and narrow artificial intelligence"']
  rank  7 M015 (queries Q6): ['narrowing -> "called narrow systems of"']
  rank  8 M016 (queries Q1): none in title/abstract
  rank  9 M012 (queries Q5): none in title/abstract
  rank 10 M026 (queries Q3): ['narrowing -> "for narrow specific tasks"']
```

rank 1、6、7、10 只靠词干还原后的 narrow 命中（narrow applications / narrow AI / narrow systems / narrow-specific tasks），与选题收窄无关。这是 Step 12 把 "narrowing of science" 放宽为 narrowing 带来的噪声。

**命令 3：写 evidence/evidence_table_v2.md 并校验（python3 内联脚本：表格与 candidates_v2.csv、authors_v2.json 逐项比对；判定依据中的引文须在对应摘要中逐字出现）**

rank 3（M003）本地无摘要，判定依据引用同一研究的 arXiv 预印本摘要（M106），并在表中注明。

```
table rows vs candidates_v2.csv / authors_v2.json: all 10 rows match
  研究问题: overlap 1 ['3'] | differ 9 | unknown 0
  作用机制: overlap 4 ['2', '3', '4', '8'] | differ 6 | unknown 0
  研究情境: overlap 1 ['7'] | differ 9 | unknown 0
  数据与方法: overlap 3 ['3', '5', '9'] | differ 7 | unknown 0
  预期发现: overlap 4 ['2', '3', '4', '8'] | differ 6 | unknown 0
quoted fragments checked: 37; not found verbatim: [('M018', '生成式 AI 在教育中')]
```

唯一未找到的是判定依据中一处加了英文引号的中文短语（不是摘要引文），已去掉引号；英文引文 36 段全部在摘要中逐字找到。

**命令 4：DOI 核验**

```bash
python3 -B scripts/verify.py --table evidence/evidence_table_v2.md
```

输出：

```
verify run at 2026-10-31T16:58:25+00:00  table=evidence/evidence_table_v2.md
[1] doi:10.2139/ssrn.4389118
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Artificial Intelligence and the Economics of Decision-Making
                 registered: - | 2023 | posted-content | authors: Naudé
      landing:   302 www.ssrn.com  -> 落地页 BLOCKED at www.ssrn.com (network policy, proxy 403)
[2] doi:10.1126/sciadv.adn5290
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the collective diversity of novel content
                 registered: Science Advances | 2024 | journal-article | authors: Doshi; Hauser
      landing:   302 www.science.org  -> 落地页 BLOCKED at www.science.org (network policy, proxy 403)
[3] doi:10.1038/s41586-025-09922-y
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Artificial intelligence tools expand scientists’ impact but contract science’s focus
                 registered: Nature | 2026 | journal-article | authors: Hao; Xu; Li
      landing:   302 www.nature.com  -> 落地页 BLOCKED at www.nature.com (network policy, proxy 403)
[4] doi:10.1145/3635636.3656204
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Homogenization Effects of Large Language Models on Human Creative Ideation
                 registered: Creativity and Cognition | 2024 | proceedings-article | authors: Anderson; Shah; Kreminski
      landing:   302 dl.acm.org  -> 落地页 BLOCKED at dl.acm.org (network policy, proxy 403)
[5] doi:10.1016/j.caeai.2025.100456
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Unveiling the dynamics of generative AI adoption: A business intelligence analysis through topic modeling-based bibliome…
                 registered: Computers and Education: Artificial Intelligence | 2025 | journal-article | authors: Aldreabi; Alhur; Al-Okaily
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[6] doi:10.1177/20563051231186353
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Artificial Intelligence and Democracy: A Conceptual Framework
                 registered: Social Media + Society | 2023 | journal-article | authors: Jungherr
      landing:   302 journals.sagepub.com  -> 落地页 BLOCKED at journals.sagepub.com (network policy, proxy 403)
[7] doi:10.47309/2713-2358-2025-4-184-195
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Issues of using artificial intelligence in scientific research of socio-economic processes
                 registered: Ufa Humanitarian Scientific Forum | 2025 | journal-article | authors: ?; Zulkarnay
      landing:   302 elibrary.ru  -> 落地页 BLOCKED at elibrary.ru (network policy, proxy 403)
[8] doi:10.1016/j.tics.2026.01.003
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · The homogenizing effect of large language models on human expression and thought
                 registered: Trends in Cognitive Sciences | 2026 | journal-article | authors: Sourati; S. Ziabari; Dehghani
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[9] doi:10.48550/arxiv.2506.21818
      crossref:  302 data.crosscite.org  (attempts: 1)  -> Crossref BLOCKED at data.crosscite.org (network policy, proxy 403)
      landing:   302 arxiv.org  -> 落地页 BLOCKED at arxiv.org (network policy, proxy 403)
[10] doi:10.3390/cancers15092573
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Artificial Intelligence in CT and MR Imaging for Oncological Applications
                 registered: Cancers | 2023 | journal-article | authors: Paudyal; Shah; Akin
      landing:   302 www.mdpi.com  -> 落地页 BLOCKED at www.mdpi.com (network policy, proxy 403)

summary crossref: Crossref BLOCKED at data.crosscite.org: 1 | 题目一致: 9
summary landing:  落地页 BLOCKED at arxiv.org: 1 | 落地页 BLOCKED at dl.acm.org: 1 | 落地页 BLOCKED at elibrary.ru: 1 | 落地页 BLOCKED at journals.sagepub.com: 1 | 落地页 BLOCKED at linkinghub.elsevier.com: 2 | 落地页 BLOCKED at www.mdpi.com: 1 | 落地页 BLOCKED at www.nature.com: 1 | 落地页 BLOCKED at www.science.org: 1 | 落地页 BLOCKED at www.ssrn.com: 1
written: verified column in evidence/evidence_table_v2.md
exit code: 1
```

**产出文件**

- `evidence/authors_v2.json` — 前 10 篇的作者（OpenAlex 题目与表中题目 10/10 一致）
- `evidence/evidence_table_v2.md` — v2 证据表与判定依据；verified 列已写入

**备注**

- 标签统计：研究问题 overlap 1（rank 3）；作用机制 overlap 4（rank 2、3、4、8）；研究情境 overlap 1（rank 7）；数据与方法 overlap 3（rank 3、5、9）；预期发现 overlap 4（rank 2、3、4、8）；无 unknown。
- Crossref：9/10 题目一致；rank 9 是 arXiv 经 DataCite 登记的 DOI，doi.org 把元数据请求转到 data.crosscite.org，该域名未放行，未能核验。落地页：出版商域名均未放行。
- 本步未判断新颖性。

---

## [2026-10-31 17:16 UTC] Step 16 — HOWTO.md、两个辅助工具、按 HOWTO 实测；打包 zip

**研究者要求（本轮）**：把整个目录打包为 zip；生成 HOWTO.md，让新同学只改 `idea/idea.md` 就能跑完整流程，写清每一步的命令。

**命令 1：新增与修改**

```
# HOWTO.md：T1–T6 每一步的命令（脚本步骤）或可粘贴的提示词（AI 助手步骤）、准备、清空示例、迭代、常见问题
# scripts/search.py：新增 --dry-run（不联网，只检查检索式语法并打印各来源实际发送的检索串）
# scripts/logrun.py：新增；运行一条命令，并把命令与输出追加到 logs/RUN_LOG.md，退出码与被运行命令相同
```

**命令 2：按 HOWTO 实测（在 scratchpad 中的干净副本里运行，不含 .git；T2 与 T5 的 AI 助手步骤用教程示例文件代替）**

```bash
mkdir -p examples && cp -r facets queries results evidence logs examples/
rm -f facets/*.md queries/*.json results/raw/*.json results/merged/*.json results/merged/*.csv evidence/*.md evidence/*.json idea/idea_v*.md
printf '# RUN_LOG\n\n> ...\n' > logs/RUN_LOG.md
python3 scripts/search.py --dry-run
python3 scripts/logrun.py "T3 检索" -- python3 scripts/search.py
python3 scripts/logrun.py "T4 合并去重" -- python3 scripts/merge.py
python3 scripts/logrun.py "T5 查作者" -- python3 scripts/authors.py --top 10
python3 scripts/logrun.py "T5 DOI 核验" -- python3 scripts/verify.py
python3 scripts/search.py --queries <错误示例> --dry-run              # 异常：语法错误
python3 scripts/logrun.py "exit test" -- python3 -c "...sys.exit(3)"  # 异常：退出码透传
python3 scripts/logrun.py "no command" --                             # 异常：用法错误
```

结果：

```
清空后只剩 idea/idea.md 与 results/merged/.gitkeep、results/raw/.gitkeep
--dry-run：6/6 queries valid (dry run, nothing sent)；退出码 0
T3：12/12 requests succeeded；退出码 0
T4：12 files, 217 raw records → 161 works；退出码 0
T5 查作者：written: evidence/authors.json；退出码 0
T5 DOI 核验：summary crossref: 题目一致: 10；退出码 0
错误检索式：0/2 queries valid（"不支持括号外的 OR"、"未登记的截断词 foo*"）；退出码 1
logrun 退出码透传：3；用法错误：退出码 1
副本的 RUN_LOG.md 中按顺序记有 T3、T4、T5 查作者、T5 DOI 核验、exit test 五条，均含命令与输出
```

**命令 3：打包（不纳入仓库）**

```
# python3 zipfile：把本目录打包为 novelty-probe.zip（顶层文件夹 novelty-probe/），
# 排除 .git/ 与 __pycache__/；保存在会话临时目录，发送给研究者
```

**产出文件**

- `HOWTO.md` — 新增
- `scripts/logrun.py` — 新增
- `scripts/search.py` — 新增 --dry-run
- `novelty-probe.zip` — 发送给研究者，不纳入仓库

**备注**：本步未检索新文献，未判断新颖性。

---

## [2026-10-31 17:25 UTC] Step 17 — 英文 README

**研究者要求（本轮）**：添加英文 README，帮助对本仓库感兴趣的人理解这个项目。

**命令 1：写入 README.md**

```
# 内容：项目简介（不判断新颖性）、三条规则、T1–T6 流程、快速开始（命令与 HOWTO.md 一致）、
#       各脚本的做法、示例运行（v1、v1 漏检诊断、v2）、局限、目录结构
# 先用 --help 核对各脚本参数；参考文献作者取自 evidence/authors_v2.json（OpenAlex）
```

**命令 2：核对 README 中的数字与事实（python3 内联脚本，读取仓库内文件）**

```
v1 raw -> works: 217 -> 161 | v2: 235 -> 191
reference paper (M003) rank in candidates_v2: 3
v2 rank 3 labels: {'研究问题': 'overlap', '作用机制': 'overlap', '研究情境': 'differ', '数据与方法': 'overlap', '预期发现': 'overlap'} | overlaps: 4
v1 table Crossref title matches: 10 / 10
RUN_LOG states 4 of v2 top 10 matched only via narrow: True
preprint abstract mentions '41.3 million research papers across natural science': True
```

**产出文件**：`README.md`；`novelty-probe.zip` 重新打包（含 README，不纳入仓库）

**备注**：README 只描述流程与已记录的结果，不含新颖性判断，不含研究者的个人信息。

---

## [2026-10-31 17:35 UTC] Step 18 — HOWTO 改为中英双语（逐段）

**研究者要求（本轮）**：把 HOWTO 改为中英文双语（逐段）的形式。

**命令 1：改写与相关修改**

```
# HOWTO.md：每段先中文后英文；表格单元格中英并列；命令只写一次；三个提示词各给中文、英文两个版本
# scripts/verify.py：标题列同时接受"题目"与"Title"（英文提示词生成的英文表头也能对照标题）
# README.md：更新对 HOWTO 语言的说明
```

**命令 2：检查（python3 内联脚本：新旧 HOWTO 的命令逐条比对；提示词成对；英文表头的 verify.py 本地测试）**

```
bash blocks: old 18, new 18; changed: 2
  - export OPENALEX_API_KEY="你的 key"
  + export OPENALEX_API_KEY="你的 key / your key"
  - export S2_API_KEY="你的 key"
  + export S2_API_KEY="你的 key / your key"
prompt blocks: 6 (Chinese 3, English 3)
verify.py with English 'Title' header -> Crossref HTTP 200 · 题目一致 · An English Test Paper；落地页 HTTP 200 (127.0.0.1) · An English Test Paper
```

**产出文件**：`HOWTO.md`（改写）、`scripts/verify.py`、`README.md`（修改）

**备注**：命令只有两处有意改动（export 示例中的占位文字）。本步未检索新文献，未判断新颖性。

---

## [2026-10-31 17:54 UTC] Step 19 — MIT 许可证与 CITATION.cff

**研究者要求（本轮）**：加 MIT 许可证和 CITATION.cff，重新打包；删除每个提交信息末尾的 Claude 会话链接。研究者告知：已开启 2FA，默认分支已改名为 main。

**命令 1：新增与修改**

```
# LICENSE：标准 MIT 文本，版权人为研究者提交记录中的公开署名 Alston-Y（不含邮箱）
# CITATION.cff：CFF 1.2.0，type software，license MIT，repository-code 为本仓库地址
# README.md：新增 License、How to cite 两节（注明 results/、evidence/ 中第三方摘要的版权不在 MIT 范围内）；目录结构补充两个文件
```

**命令 2：校验（PyYAML 装在临时目录，不进仓库）**

```
CITATION.cff parses as YAML: True | required keys present: True
  cff-version: 1.2.0 | type: software | license: MIT | authors: [{'name': 'Alston-Y'}] | repository-code: https://github.com/PadSama/novelty-probe-demo
LICENSE: MIT header: True | copyright line: Copyright (c) 2026 Alston-Y | canonical clauses present: True
```

**产出文件**：`LICENSE`、`CITATION.cff`（新增）；`README.md`（修改）

**备注**：自本步起，提交信息不再附 Claude 会话链接（研究者要求）。

---

## [2026-10-31 17:56 UTC] Step 20 — 改写提交历史：删除提交信息中的 Claude 会话链接（待研究者确认替换 main）

**研究者要求（本轮）**：删除每个提交信息末尾的 Claude 会话链接（`Claude-Session: https://claude.ai/code/session_…`）。

**命令 1：本地改写**

```bash
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --msg-filter "sed '/^Claude-Session: https:\/\/claude\.ai\/code\/session_/d'" -- claude/vigilant-faraday-odzwe4
```

**命令 2：核对（python3 内联脚本：逐个比较改写前后的提交）**

```
commits: old 20, new 20 | trees, authors, committers, dates identical; messages differ only by the removed line: True 
messages still containing a session link: 0
old -> new:
  a3b3030 -> 025de7e  Initialize novelty-probe project skeleton
  92dbdea -> 2153ec9  Add facet decomposition and six search queries
  6ff04f7 -> 693e490  Add search script; record generative-AI scope decision
  7dfda92 -> 1421842  Retry searches after network allowlist; partial results
  e4ae9ea -> 697b3f9  Switch S2 to bulk search; full search run succeeds
  5962e7c -> 7d6a5f8  Match OpenAlex on title+abstract; merge and dedupe results
  91d9d65 -> 3c35c08  Add hit statistics and top-20 candidates to merge.py
  32223cf -> 41e6676  Add evidence table for top 10 candidates and DOI verifier
  bec567e -> ac95654  Verify DOIs against Crossref metadata; fix title-match truncation
  b1de997 -> 955d6a6  Add blank difference-statement template
  6f6af38 -> bca6088  Fill section 1 of the difference statement with the closest three
  f237436 -> 4172c21  Enhance difference statement with detailed analysis
  372a9a4 -> 37be7bd  v2: management/economics context; facets and queries (T2)
  fd61c14 -> f5db846  v2: version suffix support in scripts; run v2 searches (T3)
  1a8aa64 -> 31e9ffb  v2: merge and dedupe; top-20 candidates (T4)
  6ee89cf -> f187558  v2: evidence table for top 10 candidates with DOI checks (T5)
  4495da6 -> e4b04f0  Add HOWTO.md, search.py --dry-run and scripts/logrun.py
  f65f32d -> 046360c  Add English README
  1b7dac7 -> c93b2c5  Make HOWTO bilingual (Chinese/English, paragraph by paragraph)
  2a5b5d5 -> 3943d3a  Add MIT license and CITATION.cff
```

**命令 3：推送**

```bash
git push --force-with-lease=main:1b7dac7… origin HEAD:main   # 被本环境的安全检查拒绝（Git Destructive），未执行
git push -u origin claude/vigilant-faraday-odzwe4             # 改为把改写后的历史推成新分支，不覆盖 main
```

**说明**

- 改写前已确认：会话链接只出现在提交信息中，从未出现在任何历史版本的文件内容里。
- 改写后所有提交的哈希都已改变（见上表）。本日志只追加、不改写，此前条目中的旧哈希保持原样，请按上表对照。例如 Step 4 提到的 7dfda92 现为 1421842。
- 研究者本人在 GitHub 网页上的提交（f237436 → 4172c21）因父提交改变而重写，GitHub 为网页提交加的签名随之失效。
- 远端 main 仍是改写前的历史（1b7dac7，带会话链接）。是否用新分支替换 main，由研究者决定。

**产出**：分支 `claude/vigilant-faraday-odzwe4`（改写后的完整历史，含 Step 19 的 LICENSE 与 CITATION.cff）

---

## [2026-11-01 08:59 UTC] Step 21 — 核查替换后的 main；CITATION.cff 改为个人作者格式并标注 v1.0.0

**研究者告知与要求（本轮）**：已按方案 A 替换 main，请检查；完善 About（description、website、topics）；发布 v1.0。

**命令 1：核查 main（只读：git fetch、ls-remote、log）**

```
默认分支：main；远端只剩 main（071539d），旧分支名已不存在；远端无标签
main 共 23 个提交；提交信息中的会话链接：0；改写前的旧历史（1b7dac7）不在 main 上
本会话最后推送的 d80d849 是 main 的祖先；其后为研究者在网页上的两个提交：
  d97ab3d Change copyright（LICENSE 版权人改为 Quan Yuan）
  071539d Update author name in CITATION.cff（作者改为 Quan Yuan）
  两个提交的作者邮箱均为 GitHub noreply 地址
LICENSE、CITATION.cff、README.md 均在 main 上
```

此前条目（Step 19、20）中记的版权人 Alston-Y 已由研究者改为 Quan Yuan，以 main 上的文件为准。

**命令 2：CITATION.cff 修改与校验**

```
# authors 由机构格式（name）改为个人格式（family-names: Yuan / given-names: Quan），引用可格式化为 "Yuan, Q."
# 新增 version: "1.0.0"、date-released: 2026-11-01
# 校验：从 cffconvert 2.0.0 的安装包中取出官方 CFF 1.2.0 schema，用 jsonschema 校验（均装在临时目录）
schema: cffconvert/schemas/1.2.0/schema.json (from cffconvert-2.0.0-py3-none-any.whl)
CITATION.cff valid against CFF 1.2.0 schema: True 
authors: [{'family-names': 'Yuan', 'given-names': 'Quan'}] | version: 1.0.0 | date-released: 2026-11-01 | license: MIT
```

**产出文件**：`CITATION.cff`（推送到分支 `claude/vigilant-faraday-odzwe4`，main 受保护，需研究者通过 PR 合并）

**备注**：About 的文字与 v1.0.0 的发布由研究者在 GitHub 网页上操作，本环境没有修改仓库设置或创建 Release 的工具。本仓库没有可发布的软件包，Packages 不需要。

---

## [2026-11-01 09:20 UTC] Step 22 — CITATION.cff 加入作者 ORCID

**研究者告知与要求（本轮）**：已手动合并 PR #1；其余配置（About 等）已完成；提供 ORCID 0009-0009-3011-3739，加入 CITATION.cff。

**命令 1：核查远端（只读）**

```
main：3f00b7a "Merge pull request #1 from PadSama/claude/vigilant-faraday-odzwe4"（合并提交，父提交 071539d、2ec606a）
标签：v1.0.0 → 3f00b7a；分支 claude/vigilant-faraday-odzwe4 仍在 2ec606a（已并入 main）
main 上提交信息中的会话链接：0
```

**命令 2：加入 ORCID 并校验**

```
# authors 下新增 orcid: "https://orcid.org/0009-0009-3011-3739"
# 校验：ORCID 校验位（ISO 7064 MOD 11-2）；官方 CFF 1.2.0 schema（同 Step 21 的方法）
ORCID 0009-0009-3011-3739: check digit valid (ISO 7064 MOD 11-2)
CITATION.cff valid against CFF 1.2.0 schema: True 
authors: [{'family-names': 'Yuan', 'given-names': 'Quan', 'orcid': 'https://orcid.org/0009-0009-3011-3739'}]
```

**产出文件**：`CITATION.cff`（推送到分支 `claude/vigilant-faraday-odzwe4`，需研究者通过 PR 合并）

**备注**：v1.0.0 的标签已打在 3f00b7a 上，这一版的 CITATION.cff 不含 ORCID；本次改动进入 main 后，"Cite this repository" 与之后的版本会带上 ORCID。

---

## [2026-11-02 07:23 UTC] Step 23 — 梳理项目并准备本地移植的交接（ZCode + GLM 5.3）

**研究者告知与要求（本轮）**：PR 已合并，远端只剩 main。研究者将在本地 ZCode 客户端用 GLM 5.3 完成移植，要求梳理整个项目，整理必要的说明与交接文档。

**命令 1：同步与盘点（只读）**

```
main：a104d4d（PR #2 合并后，研究者另改了 CITATION.cff 标题的大小写）；远端分支只有 main
仓库跟踪 52 个文件；文档中写死 Claude Code 的地方：HOWTO 多处、README 1 处
```

**命令 2：脚本的健壮性修改（换用其他 AI 助手后最易出错之处）**

```
# search.py：新增 load_queries()，检查 JSON 格式、id 必须为 Q+数字（merge.py 只读这种文件名）且不重复、
#            query 非空、purpose 取值；问题一次列全，退出码 2。--ids 中有不存在的 id 时报错（原先静默跑 0 条）
# merge.py、authors.py、search.py：路径显示改用 rel()（输出目录不在项目内时不再报错）
# authors.py：读取候选文件后正确关闭（自检发现的 ResourceWarning）
```

**命令 3：离线自检 tests/test_offline.py（标准库 unittest；不联网、不改动仓库文件）**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests
```

```
----------------------------------------------------------------------
Ran 21 tests in 2.178s

OK
```

覆盖：检索式校验与两种语法转换、记录字段提取、请求重试、检索主流程（模拟 API）、合并去重与排序、用已提交的原始结果复现已提交的合并结果（v1、v2 逐字节一致）、作者查询（模拟 API）、DOI 核验（本机模拟服务器）、logrun、仓库数据文件格式。另加 `.gitignore`（忽略 `__pycache__`）。

**命令 4：文档**

```
# 新增 AGENTS.md：给任何 AI 编程助手的规则与文件约定
# 新增 HANDOFF.md：现状、本地环境准备（key、代理、证书、自检、冒烟测试）、ZCode 用法、数据约定、
#                 脚本速查、设计决策、已知问题、Git 与发布、检查清单
# HOWTO.md、README.md：不再写死 Claude Code，改为通用的 AI 编程助手；加入自检命令；目录表补充新文件
# PROJECT.md：目录表补充 scripts/、tests/ 与其他文档
```

**命令 5：文档一致性检查（python3 内联脚本）**

```
script commands checked: 26; unknown scripts/flags: none
文档中只写文件名的路径均能在仓库中找到对应文件；其余"找不到"的条目是列名、API 路径或家目录文件
修改后再次运行自检：Ran 21 tests … OK
```

**产出文件**

- `AGENTS.md`、`HANDOFF.md`、`tests/test_offline.py`、`.gitignore`（新增）
- `scripts/search.py`、`scripts/merge.py`、`scripts/authors.py`、`HOWTO.md`、`README.md`、`PROJECT.md`（修改）

**备注**：推送到分支 `claude/vigilant-faraday-odzwe4`，需研究者通过 PR 合并。下一步编号为 Step 24。
