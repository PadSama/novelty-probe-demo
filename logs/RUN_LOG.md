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
