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

---

## [2026-11-02 07:48 UTC] Step 24 — 针对遗留问题的调研（进行中）与先行改进：文本匹配、质量检查、核验回退、版本补全

**研究者要求（本轮）**：自行解决 `HANDOFF.md` 第 9 节列出的遗留问题；可以查 GitHub 上的类似项目和论文；先调研、再计划、最后执行。

本步只做了不依赖调研结论、风险低的部分；检索式 NOT 的语法转换、排序、预印本合并、引文追踪等待调研完成后写入改进计划再实施。

**命令 1：网络与 API 探测（python3 内联脚本，只读）**

```
可访问：api.openalex.org（key 由环境注入）、api.semanticscholar.org（无 key，限流）、api.crossref.org、doi.org、
        api.github.com、raw.githubusercontent.com
被网络策略拦截：export.arxiv.org、api.datacite.org、data.crosscite.org、www.ebi.ac.uk、api.unpaywall.org、出版商站点
```

**命令 2：缺摘要候选的补全来源（python3 内联脚本，只读）**

```
candidates without abstract: 5 (v1+v2 top-20)
  v1 rank  1 M010 doi=10.1038/s41586-025-09640-5 | abstract chars: crossref 0, openalex 0, s2 0
  v1 rank 12 M037 doi=10.1007/978-981-15-1420-3_90 | abstract chars: crossref 0, openalex 0, s2 0
  v1 rank 14 M034 doi=10.1007/s13132-022-00920-3 | abstract chars: crossref 0, openalex 0, s2 0
  _v2 rank 3 M003 doi=10.1038/s41586-025-09922-y | abstract chars: crossref 0, openalex 0, s2 0
  _v2 rank 13 M030 doi=10.5465/amj.2008.34789630 | abstract chars: crossref 0, openalex 0, s2 0
```

按 DOI 从三个来源都取不到这 5 篇的摘要。改为按题目在 OpenAlex 查同一研究的其他版本：v2 M003（Hao 等，Nature）找到 arXiv 预印本（doi:10.48550/arxiv.2412.07727，有摘要）；同一结果里还有一封题为 "Re: Artificial Intelligence Tools Expand …" 的读者来信（doi:10.1016/j.eururo.2026.04.004），不是同一研究，须排除。

**命令 3：Porter 词干还原的独立实现与 snowballstemmer 3.1.1（"porter"）逐词对照（python3 内联脚本）**

```
words compared: 9034; mismatches vs snowballstemmer 'porter': 0 []
fixture pairs saved: 321
```

**命令 4：新增与修改的脚本**

```
# 新增 scripts/textmatch.py：只用标准库的文本匹配模块——Porter 词干还原；按词干匹配短语、按前缀匹配截断词；
#   判断记录是否满足检索式（含 NOT 组）；BM25 打分；识别同一研究的不同版本（去掉末尾版本说明括注后标题相同，
#   且不是 Re:、更正、回复、评论等独立条目）
# 新增 scripts/qa.py：检索质量检查（第 9 节问题 8）。逐个原始结果文件统计标题+摘要满足原检索式的记录数
# 新增 scripts/enrich.py：从同一研究的其他版本补摘要与 arXiv ID（第 9 节问题 5）。按题目查 OpenAlex，要求标题相同
#   （≥6 个词）、年份相差 ≤3、至少一位作者同姓；结果连同来源写到 evidence/enrichment{suffix}.json，不改动 results/
# scripts/verify.py：Crossref 核验失败时改查 OpenAlex（按 DOI），解决 arXiv 等 DataCite DOI 无法核验（问题 7）；
#   落地页从 https:// 跳到 http:// 时改用 https://（Emerald、IEEE，问题 6）；新增 --no-landing
# scripts/search.py：新增 parse_query()，可解析 "… AND NOT (a OR b)" 形式的排除组（只做解析；
#   到 OpenAlex、S2 语法的转换尚未实现，暂不要在检索式里使用 NOT）
```

**命令 5：试运行（写入临时目录，不改动仓库文件）**

```
verify.py --no-landing，临时表（v2 rank 3、9）：
  [9] doi:10.48550/arxiv.2506.21818
      crossref:  302 data.crosscite.org -> Crossref BLOCKED at data.crosscite.org (network policy, proxy 403)
      openalex:  -> OpenAlex · 题目一致 · A systematic review of research on large language models for computer programming education
verify.py，临时表（v1 rank 6、8）：
  [6] landing: 302 www.emerald.com (http→https) -> 落地页 BLOCKED at www.emerald.com (network policy, proxy 403)
  [8] landing: 302 ieeexplore.ieee.org (http→https) -> 落地页 BLOCKED at ieeexplore.ieee.org (network policy, proxy 403)
  （原先为 "ERROR at http://…: Name or service not known"；现在与其他出版商一样，只是被本环境拦截）
enrich.py，v2 前 20：missing abstracts: 2 → added from another version: 1（M003，来自 arXiv 2412.07727，作者核对 shared）；
  arXiv IDs added: 1
enrich.py，v1 前 20：missing abstracts: 3 → added: 0（M010、M037、M034 在 OpenAlex 中没有其他版本）
qa.py 复现 Step 4、13、15 的内联检查结果：v1 177/217（有摘要者 169/178）；v2 181/235（170/170）
```

**命令 6：离线自检**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests
```

```
Ran 35 tests in 3.984s

OK
```

新增 `tests/test_pipeline.py`（词干还原与 snowballstemmer 的 321 对对照、检索词匹配、BM25、版本标题识别、NOT 解析、qa.py 复现已记录的数字、enrich.py 的版本筛选），`tests/fixtures/porter_pairs.json`；`tests/test_offline.py` 增加 OpenAlex 回退、--no-landing、http→https 的测试，核验测试不再访问真实的 OpenAlex。

**产出文件**

- `scripts/textmatch.py`、`scripts/qa.py`、`scripts/enrich.py`、`tests/test_pipeline.py`、`tests/fixtures/porter_pairs.json`（新增）
- `scripts/verify.py`、`scripts/search.py`、`tests/test_offline.py`（修改）

---

## [2026-11-02 08:05 UTC] Step 25 — 按研究者的标准修订证据表的"研究问题"面

**研究者意见**（`evidence/difference_statement.md` 第 2 节）："证据表把 rank 2、rank 4 的'研究问题'标为 differ，我不同意：去掉情境之后，问题是同一个——个人用 AI，集体是否趋同。"

**做了什么**

- 两张证据表的标注规则中，"研究问题"面的 overlap 条件改为：去掉研究情境后问题相同（个人使用 AI，集体层面的产出是否趋同、多样性是否下降）；对象与学科的不同记在"研究情境"面。
- 按新条件逐篇复核两张表的 20 行（依据摘要原文）：
  - v1：rank 2（M031，Doshi & Hauser）、rank 4（M024，Anderson 等）differ → overlap；
  - v2：rank 2（M027，同 v1 rank 2）、rank 4（M021，同 v1 rank 4）、rank 8（M016，Sourati 等，"amplifying convergence as all people increasingly rely on the same models across contexts"）differ → overlap；
  - 其余各篇不变（问的不是"个人用 AI、集体是否趋同"：如概念框架、文献计量综述、AI 应用综述）。
- v2 rank 8 是助手按同一标准做的推断，研究者只点名了 v1 的 rank 2、rank 4，已在表中注明请研究者确认。
- 判定依据中改动的条目注明"修订，原为 differ"；两张表末尾新增"修订记录"。
- `evidence/difference_statement.md` 第 1 节：rank 2、rank 4 两行按修订后的证据表重新复制，选择规则中的面数由 2 改为 3，加修订说明；入选的三篇不变。第 2、3 节（研究者填写）未改动。

**校验**：`python3 -m unittest tests.test_offline.TestRepositoryData` → OK（两张表各 10 行，五个面的取值合法）。

**产出文件**

- `evidence/evidence_table.md`、`evidence/evidence_table_v2.md`、`evidence/difference_statement.md`（修改）

---

## [2026-11-02 08:24 UTC] Step 26 — 调研结论与改进计划

**做了什么**：三个调研子任务（召回与引文追踪；预印本与正式版的识别；排序、降噪与词干还原）各自查阅 GitHub 上的同类项目与方法论文献，并对 OpenAlex、Semantic Scholar 做实时请求，结论写入 `docs/IMPROVEMENT_PLAN.md`（问题 → 原因 → 依据 → 方案 → 状态 → 验收标准）。计划与第 27 步的实施交替进行，状态栏按实施结果更新。

**主要结论**（详见计划文件）

- 召回：从 v1 证据表的种子出发，一步追踪（前向、后向、OpenAlex related_works、S2 推荐接口）都找不到 Hao 等；两步共被引可以找到，但结果取决于过滤引用者所用的词组（这一过滤方式是在知道目标的情况下试出的，只算一个正例）。
- 降噪：OpenAlex 的大写 NOT 有效，小写 not 与 - 会把排除变成必须包含；S2 用 `-(…)`。v2 Q3 加 NOT 后 OpenAlex 299 → 247、S2 123 → 111，前 10 的噪声 4 → 1。
- 合并：Hao 等两个版本未合并只因预印本标题末尾的 "(Just accepted by Nature…)"；保守规则在 v1、v2 数据上只新增这一对合并。
- 排序：RRF 消除并列但不能去噪；S2 应在取回的全部记录上本地重排；两个来源都用本地 BM25 时参考文献会因缺摘要掉到第 23 名，所以 OpenAlex 保留 API 排序。
- 词干还原：`textmatch.porter_stem` 与 Snowball porter 在 Snowball 的 42,603 词测试表上完全一致；两个 API 的匹配更像 KStem，质量检查的比例因此略偏高。

**命令：文献 DOI 核验（python3 内联脚本，按 DOI 请求 api.crossref.org/works/<doi>，查不到时查 OpenAlex）**

```
排序与降噪 14 个、去重与版本识别 15 个、召回与引文追踪 16 个，共 45 个 DOI：全部 OK（44 个 Crossref，1 个 arXiv DOI 经 OpenAlex）
例：OK crossref | 10.1145/1571941.1572114 | 2009 | Cormack | Reciprocal rank fusion outperforms condorcet and individual rank learning methods
    OK crossref | 10.1186/s12915-023-01686-z | 2023 | Hair | The Automated Systematic Search Deduplicator (ASySD) …
    OK crossref | 10.1136/bmj-2023-078384 | 2024 | Hirt | Guidance on terminology, application, and reporting of citation searching: the TARCiS statement
    OK openalex | 10.48550/arXiv.2301.10140 | 2023 | Rodney Kinney | The Semantic Scholar Open Data Platform
```

**产出文件**：`docs/IMPROVEMENT_PLAN.md`（新增）

---

## [2026-11-02 08:28 UTC] Step 27 — 按计划实施：NOT、S2 本地重排、合并新方法、两步共被引、结果比较

**命令 1：脚本修改与新增**

```
# search.py：AND NOT (…) 译为 OpenAlex 原样（大写 NOT）、S2 的 + -(…)；OpenAlex 返回的 x_query.oql 中没有 NOT 时报错、不保存；
#   拒绝小写运算符（and/or/not）和以 - 或 ! 开头的词。S2 改为翻页取回全部命中（最多 3000 条）后本地重排：
#   满足的包含组数 → BM25（k1=1.2，b=0.75）→ 被引次数；无摘要记录中标题命中（组数 − 1）个组的按比例穿插。
#   每条 S2 记录附 local_rank 字段（命中组数、BM25、是否有摘要、被引次数）
# textmatch.py：版本识别改为调研给出的保守规则（去掉末尾发表状态括注、去重音、来信/变体/数据集/DOI 冲突/年份差/摘要 Jaccard）
# merge.py：默认方法改为——DOI 规范化（去掉 ?utm_source=… 与 /full/html）、版本识别（自动合并或标出待核对）、
#   year 取正式发表版本、year_first 取最早版本、按 RRF（k=60）排序并以 BM25 打破并列；--legacy 复现 Step 6 / 14 的方法
# snowball.py：新增两步共被引（--cocite --citer-filter …，读者来信与更正不计）；输出改名为 chase_<标签>{suffix}
# 新增 compare.py：比较几轮结果（已知文献名次、截断处并列、前 K 篇满足检索式 / 噪声 / 生成式 AI 关键词 / 摘要 / 年份）
# qa.py：注明是 Porter 对 API 的 KStem 匹配的近似
```

**命令 2：实时检查（写入临时目录，不改动仓库文件）**

```
search.py，v2 检索式加 AND NOT ("narrow AI" OR "narrow artificial intelligence")，只跑 Q3：
  Q3 openalex total_hits 247；semanticscholar total_hits 111（与调研子任务独立测得的数字一致）
  S2 本地重排后的前 25：24 篇有摘要且满足全部 3 个包含组；Hao 等 Nature 版（无摘要，标题命中 2 组）穿插在第 13 位；
  arXiv 预印本第 2 位。原先按被引次数取的前 25 含 1984、1997 年的文献
merge.py（默认方法）用已提交的原始结果：
  v2：新增版本合并 1 组（Hao 等 Nature 版 + arXiv 版，year 2026、year_first 2024，带上预印本摘要）；
      待核对 2 对（IEEE DataPort 数据集 / 同名 TechRxiv 预印本；ICAITE 会议论文 / 同名 Zenodo 存档）
  v1、v2：旧方法按标题合并的 7 组各保留 6 组，只拆开 DataPort 一对；
  两个来源年份不一致的 4 个 DOI 都取到正式发表年份（含 OpenAlex 把 1993 年 HICSS 论文记为 2002 的一例）
snowball.py --from-evidence evidence/evidence_table.md --cocite --citer-filter 'scientist*'（种子：v1 rank 2、4）：
  citing works: 1083 cite the seeds; 13 pass the filter 'scientists'; 1 letters/replies excluded; 12 citers used
  co-cited: 558 works cited by the citers; 15 cited by at least 2
  cocited #1 support 5  doi:10.1038/s41586-025-09922-y  Artificial intelligence tools expand scientists' impact but contract …
compare.py --runs ,_v2（已提交结果）：v2 前 10 的噪声 4 篇（与 Step 15 一致）；Hao 等 v1 中无，v2 中第 3 名，其 arXiv 版单列第 60 名
```

过滤词组 scientist* 取自 v1 facets.md 研究情境面的"使用者"一词（F3 #5），依据是两篇种子与想法恰在研究情境面不同；但调研子任务已先测出这一过滤能找到 Hao 等，所以这不是独立验证。

**命令 3：离线自检**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests
```

```
Ran 44 tests

OK
```

新增测试：NOT 转换与 oql 检查、S2 本地重排与翻页、合并新方法（版本、年份、待核对、RRF）、两步共被引、compare.py；`test_reproduces_committed_merge_outputs` 改为用 `--legacy` 复现已提交结果（仍逐字节一致）。

**产出文件**

- `scripts/compare.py`（新增）
- `scripts/search.py`、`scripts/textmatch.py`、`scripts/merge.py`、`scripts/snowball.py`、`scripts/qa.py`、`tests/test_offline.py`、`tests/test_pipeline.py`、`docs/IMPROVEMENT_PLAN.md`（修改）

---

## [2026-11-02 08:47 UTC] Step 28 — v1b 检索前语法检查（v1 检索式不变）

**命令**

```bash
python3 scripts/search.py --queries queries/queries.json --dry-run
```

**输出**（退出码 0）

```
Q1 [component]
  openalex:        ("large language models" OR "generative AI") AND (homogenization OR homogenisation OR "algorithmic monoculture" OR "collective diversity")
  semanticscholar: ("large language models" | "generative AI") + (homogeniz* | homogenis* | "algorithmic monoculture" | "collective diversity")
Q2 [component]
  openalex:        ("narrowing of science" OR "topic concentration" OR "topic diversity" OR "research diversification") AND ("science of science" OR bibliometrics)
  semanticscholar: ("narrowing of science" | "topic concentration" | "topic diversity" | "research diversification") + ("science of science" | bibliometric*)
Q3 [application]
  openalex:        ("AI in science" OR "AI for science" OR "large language models" OR "machine learning") AND ("research topic selection" OR "problem choice" OR "direction of science")
  semanticscholar: ("AI in science" | "AI for science" | "large language models" | "machine learning") + ("research topic selection" | "problem choice" | "direction of science")
Q4 [application]
  openalex:        ("streetlight effect" OR "Matthew effect" OR "exploration-exploitation") AND ("AI for science" OR "large language models" OR "generative AI") AND scientists
  semanticscholar: ("streetlight effect" | "Matthew effect" | "exploration-exploitation") + ("AI for science" | "large language models" | "generative AI") + scientist*
Q5 [method]
  openalex:        ("LLM-generated text" OR "topic modeling" OR "difference-in-differences") AND ("science of science" OR bibliometrics) AND ("large language models" OR "generative AI")
  semanticscholar: ("LLM-generated text" | "topic modeling" | "difference-in-differences") + ("science of science" | bibliometric*) + ("large language models" | "generative AI")
Q6 [concurrent]
  openalex:        ("AI in science" OR "large language models" OR "generative AI") AND ("topic diversity" OR "narrowing of science" OR "collective diversity" OR disruptiveness OR "research diversification") AND (scientists OR "science of science")
  semanticscholar: ("AI in science" | "large language models" | "generative AI") + ("topic diversity" | "narrowing of science" | "collective diversity" | disruptiveness | "research diversification") + (scientist* | "science of science")

6/6 queries valid (dry run, nothing sent)
```

---

## [2026-11-02 08:47 UTC] Step 29 — v1b 检索（v1 检索式；OpenAlex 按 API 相关度，S2 取回全部命中后本地重排）

**命令**

```bash
python3 scripts/search.py --queries queries/queries.json --suffix _v1b
```

**输出**（退出码 0）

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex               785    25     0  results/raw/openalex_Q1_v1b.json
Q1    component   semanticscholar        392    25     1  results/raw/semanticscholar_Q1_v1b.json
Q2    component   openalex                38    25     0  results/raw/openalex_Q2_v1b.json
Q2    component   semanticscholar         43    25     1  results/raw/semanticscholar_Q2_v1b.json
Q3    application openalex                 8     8     1  results/raw/openalex_Q3_v1b.json
Q3    application semanticscholar          9     9     0  results/raw/semanticscholar_Q3_v1b.json
Q4    application openalex                 1     1     0  results/raw/openalex_Q4_v1b.json
Q4    application semanticscholar          1     1     0  results/raw/semanticscholar_Q4_v1b.json
Q5    method      openalex                50    25     0  results/raw/openalex_Q5_v1b.json
Q5    method      semanticscholar         45    25     1  results/raw/semanticscholar_Q5_v1b.json
Q6    concurrent  openalex                63    25     1  results/raw/openalex_Q6_v1b.json  [year>=2023]
Q6    concurrent  semanticscholar         23    23     1  results/raw/semanticscholar_Q6_v1b.json  [year>=2023]

12/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25: OpenAlex by API relevance, S2 re-ranked locally by relevance); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
```

---

## [2026-11-02 08:47 UTC] Step 30 — v1b 检索质量检查

**命令**

```bash
python3 scripts/qa.py --suffix _v1b
```

**输出**（退出码 0）

```
file                                  n abstract  conform (all)  conform (with abstract)
openalex_Q1_v1b.json                 25       20   25/25 (100%)             20/20 (100%)
openalex_Q2_v1b.json                 25       16    16/25 (64%)             16/16 (100%)
openalex_Q3_v1b.json                  8        7      7/8 (88%)               7/7 (100%)
openalex_Q4_v1b.json                  1        0       0/1 (0%)                      0/0
openalex_Q5_v1b.json                 25       21    21/25 (84%)             21/21 (100%)
openalex_Q6_v1b.json                 25       23    22/25 (88%)              22/23 (96%)
semanticscholar_Q1_v1b.json          25       23   25/25 (100%)             23/23 (100%)
semanticscholar_Q2_v1b.json          25       21    21/25 (84%)             21/21 (100%)
semanticscholar_Q3_v1b.json           9        7      4/9 (44%)                4/7 (57%)
semanticscholar_Q4_v1b.json           1        0       0/1 (0%)                      0/0
semanticscholar_Q5_v1b.json          25       23    24/25 (96%)             23/23 (100%)
semanticscholar_Q6_v1b.json          23       21    18/23 (78%)              18/21 (86%)

total: 183/217 records conform; among records with an abstract: 175/182  (Porter approximation of the APIs' KStem-like matching)
```

---

## [2026-11-02 08:47 UTC] Step 31 — v1b 合并去重与排序（默认方法：版本识别、正式发表年份、RRF）

**命令**

```bash
python3 scripts/merge.py --suffix _v1b
```

**输出**（退出码 0）

```
inputs:     12 files, 217 raw records
merged:     164 works (duplicates removed: 53; groups linked as versions by title: 6; pairs flagged for review: 2)
  version link  M089: openalex_Q1_v1b#3 + openalex_Q1_v1b#9
  version link  M112: openalex_Q1_v1b#8 + openalex_Q1_v1b#14
  version link  M111: openalex_Q1_v1b#10 + openalex_Q1_v1b#18
  version link  M142: openalex_Q2_v1b#9 + openalex_Q2_v1b#11
  version link  M008: openalex_Q5_v1b#13 + openalex_Q5_v1b#14
  version link  M072: openalex_Q6_v1b#12 + openalex_Q6_v1b#13
  review        M018 / M103: same title, but two different non-preprint DOIs
  review        M041 / M075: same title, but one record has a data-repository DOI
id_status:  DOI 140 | arXiv 18 | UNVERIFIED 6
sources:    openalex only 57 | semanticscholar only 67 | both 40
per query:  Q1 39 | Q2 33 | Q3 12 | Q4 1 | Q5 41 | Q6 38
written:    results/merged/merged_v1b.json, results/merged/candidates_v1b.csv (top 20; sorted by RRF, then BM25)
cutoff:     works sharing the #20 score (RRF and BM25): 1

rank  id        rrf   bm25 conf hits year  identifier                               title
   1  M015   0.0328   0.00    0    2 2025  doi:10.1038/s41586-025-09640-5           A multimodal robotic platform for multi-element electrocat…
   2  M001   0.0320   8.88    1    2 2026  doi:10.1038/s41598-026-54348-9           A temporal adaptive dictionary-constrained LDA and Bi-cali…
   3  M007   0.0318   5.72    1    2 2026  doi:10.1177/01655515261461741            From connectivity to insight: A graph neural network–large…
   4  M026   0.0318   5.64    1    2 2024  doi:10.1126/sciadv.adn5290               Generative AI enhances individual creativity but reduces t…
   5  M031   0.0315   5.22    1    2 2023  doi:10.18559/ebr.2023.2.732              The rise of generative AI and possible effects on the econ…
   6  M002   0.0311   4.68    1    2 2026  doi:10.32599/apjb.17.1.202603.1          Analysis of Generative AI Research Trends in Korean Busine…
   7  M025   0.0311   4.50    1    2 2025  doi:10.1016/j.caeai.2025.100456          Unveiling the dynamics of generative AI adoption: A busine…
   8  M013   0.0310   4.62    1    2 2026  doi:10.48550/arxiv.2606.10587            Towards Diverse Scientific Hypothesis Search with Large La…
   9  M017   0.0310   1.31    0    2 2025  doi:10.1007/s11701-025-03108-4           Bibliometric analysis of robotic-assisted hepatobiliary an…
  10  M011   0.0309   6.16    1    2 2026  doi:10.1111/ssm.70041                    Prompt‐a‐Scientist: Using Generative AI to Disrupt Stereot…
  11  M038   0.0306   5.17    1    2 2018  doi:10.1186/s13643-018-0709-6            Evaluating characteristics of PROSPERO records as predicto…
  12  M040   0.0303   9.55    1    2 1993  doi:10.1109/hicss.1993.270676            Drug design using inductive logic programming
  13  M037   0.0302   4.25    1    2 2018  doi:10.1016/j.ecolmodel.2018.04.020      Bibliometric review of ecological network analysis: 2010–2…
  14  M032   0.0301   4.28    1    2 2022  doi:10.1007/s11769-022-1265-5            Bibliometric Review of Biodiversity Offsetting During 1992…
  15  M006   0.0299   5.11    1    2 2026  doi:10.56831/psen-08-274                 Does Generative AI Stifle Creativity? Convergence and Homo…
  16  M035   0.0296   0.00    0    2 2020  doi:10.1007/978-981-15-1420-3_90         Feature Selection Algorithms in Medical Data Classificatio…
  17  M021   0.0294   4.87    1    2 2025  doi:10.51574/ijrer.v5i1.4271             Make A Match Learning Model on Learning Outcomes in Elemen…
  18  M003   0.0293   4.62    1    2 2026  doi:10.37630/bijee.v4i1.4446             Artificial Intelligence in English Language Teaching (2018…
  19  M034   0.0292   3.69    1    2 2020  doi:10.1080/08911762.2020.1765444        A Systematic Literature Review and Bibliometric Analysis o…
  20  M036   0.0290   4.85    1    2 2020  doi:10.1108/bij-04-2020-0137             Service supply chain: from bibliometric analysis to conten…
```

---

## [2026-11-02 08:48 UTC] Step 32 — v1b 从其他版本补摘要（前 20 篇）

**命令**

```bash
python3 scripts/enrich.py --top 20 --candidates results/merged/candidates_v1b.csv --out evidence/enrichment_v1b.json
```

**输出**（退出码 0）

```
  1 M015  needs=abstract,arxiv_id      versions=0 found=- 
  2 M001  needs=arxiv_id               versions=0 found=- 
  3 M007  needs=arxiv_id               versions=0 found=- 
  4 M026  needs=-                      versions=0 found=- 
  5 M031  needs=arxiv_id               versions=0 found=- 
  6 M002  needs=arxiv_id               versions=0 found=- 
  7 M025  needs=arxiv_id               versions=0 found=- 
  8 M013  needs=-                      versions=0 found=- 
  9 M017  needs=abstract,arxiv_id      versions=0 found=- 
 10 M011  needs=arxiv_id               versions=0 found=- 
 11 M038  needs=arxiv_id               versions=0 found=- 
 12 M040  needs=arxiv_id               versions=0 found=- 
 13 M037  needs=arxiv_id               versions=0 found=- 
 14 M032  needs=arxiv_id               versions=0 found=- 
 15 M006  needs=arxiv_id               versions=0 found=- 
 16 M035  needs=abstract,arxiv_id      versions=0 found=- 
 17 M021  needs=arxiv_id               versions=0 found=- 
 18 M003  needs=arxiv_id               versions=0 found=- 
 19 M034  needs=arxiv_id               versions=0 found=- 
 20 M036  needs=arxiv_id               versions=0 found=- 

missing abstracts: 3 → added from another version: 0; arXiv IDs added: 0; DOIs suggested (verify before use): 0
written: evidence/enrichment_v1b.json
```

---

## [2026-11-02 08:48 UTC] Step 33 — v1b 引文追踪：一步（种子取 v1 证据表中至少 2 个面为 overlap 的文献）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

pool: 1171 works linked to the seeds (66 linked to more than one seed)
already in search results (results/merged/merged_v1b.json): 7
written: results/raw/chase_C1_v1b.json, results/merged/chase_C1_v1b.csv

path     rank  score    sim in_search  identifier                               title
onehop      1      2  0.326      M112  doi:10.1016/j.chbah.2025.100207          Homogenizing effect of large language models (LLMs) on creative divers
onehop      2      2  0.279      M133  doi:10.1145/3715928.3737481              How AI Ideas Affect the Creativity, Diversity, and Evolution of Human 
onehop      3      2  0.267         -  doi:10.1145/3706598.3713146              Timing Matters: How Using LLMs at Different Timings Influences Writers
onehop      4      2  0.254         -  doi:10.1016/j.yjoc.2026.100142           Perceived human agency and AI-assisted idea generation
onehop      5      2  0.247         -  doi:10.1145/3803784.3816857              The Role of Human Agency in Human-AI Co-Creativity
onehop      6      2  0.239         -  doi:10.1073/pnas.2504966122              Echoes in AI: Quantifying lack of plot diversity in LLM outputs
onehop      7      2  0.234         -  doi:10.1145/3772318.3791185              Partnering with Generative AI: Experimental Evaluation of Model-Led an
onehop      8      2  0.229         -  doi:10.1016/j.chbah.2026.100289          Diverse AI personas can mitigate the homogenization effect in human-AI
onehop      9      2  0.216         -  doi:10.1145/3706598.3714198              Human Creativity in the Age of LLMs: Randomized Experiments on Diverge
onehop     10      2  0.211      M111  doi:10.1177/00491241251327130            Generative AI Meets Open-Ended Survey Responses: Research Participant 
onehop     11      2  0.211         -  doi:10.1145/3708359.3712094              One Does Not Simply Meme Alone: Evaluating Co-Creativity Between LLMs 
onehop     12      2  0.209         -  doi:10.1016/j.tsc.2025.101870            Large language models show both individual and collective creativity c
onehop     13      2  0.207         -  doi:10.1016/j.tsc.2025.101958            Evaluating AI-assisted creative ideation: A crossover study in higher 
onehop     14      2  0.194         -  doi:10.1145/3746175.3746189              Has AI Surpassed Humans in Creative Idea Generation? A Meta-Analysis
onehop     15      2  0.185         -  doi:10.1038/s41562-025-02331-1           A large-scale comparison of divergent creativity in humans and large l
onehop     16      2  0.172         -  doi:10.1057/s41599-025-05867-9           Inspiration booster or creative fixation? The dual mechanisms of LLMs 
onehop     17      2  0.166         -  doi:10.1145/3698061.3726910              From Pen to Prompt: How Creative Writers Integrate AI into their Writi
onehop     18      2  0.159         -  doi:10.1080/17501229.2026.2678315        When LLMs meet creativity: rethinking GFL writing through Human–LLM co
onehop     19      2  0.158         -  doi:10.55737/tk/v5i1.51147               Students’ Creativity, Originality, and Use of Generative AI in Irish A
onehop     20      2  0.152         -  doi:10.1145/3772318.3791329              Decoupling of Usefulness and Novelty: Evaluating the Impact of Generat
```

---

## [2026-11-02 08:48 UTC] Step 34 — v1b 引文追踪：两步共被引（引用者按 v1 研究情境面的使用者一词 scientist* 过滤）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b --cocite --citer-filter 'scientist*'
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

citing works: 1083 cite the seeds; 13 pass the filter 'scientists'; 1 letters/replies excluded; 12 citers used
co-cited: 558 works cited by the citers; 15 cited by at least 2
already in search results (results/merged/merged_v1b.json): 0
written: results/raw/chase_C2_v1b.json, results/merged/chase_C2_v1b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      5  0.040         -  doi:10.1038/s41586-025-09922-y           Artificial intelligence tools expand scientists’ impact but contract s
cocited     2      3  0.112         -  doi:10.1038/s43588-025-00906-6           SciSciGPT: advancing human–AI collaboration in the science of science
cocited     3      3  0.030         -  doi:10.1038/s41562-024-02020-5           Quantifying the use and potential benefits of artificial intelligence 
cocited     4      3  0.085         -  doi:10.3390/soc15010006                  AI Tools in Society: Impacts on Cognitive Offloading and the Future of
cocited     5      3  0.093         -  doi:10.1126/science.adh2586              Experimental evidence on the productivity effects of generative artifi
cocited     6      2  0.177         -  doi:10.1145/3614419.3644000              The Role of Interface Design on Prompt-mediated Creativity in Generati
cocited     7      2  0.263         -  doi:10.48550/arxiv.2409.04109            Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with
cocited     8      2  0.354         -  doi:10.2139/ssrn.4526071                 AI and Its Impact on Creativity and Diversity: An Empirical Study of L
cocited     9      2  0.213         -  doi:10.1038/s41598-023-40858-3           Best humans still outperform artificial intelligence in a creative div
cocited    10      2  0.158         -  doi:10.1073/pnas.2314021121              Can Generative AI improve social science?
cocited    11      2  0.056         -  doi:10.1287/orsc.2021.1549               To Engage or Not to Engage with AI for Critical Judgments: How Profess
cocited    12      2  0.018         -  doi:10.1038/s41586-024-07146-0           Artificial intelligence and illusions of understanding in scientific r
cocited    13      2  0.028         -  doi:10.2139/ssrn.4573321                 Navigating the Jagged Technological Frontier: Field Experimental Evide
cocited    14      2  0.127         -  doi:10.1017/cbo9780511807916.003         The Concept of Creativity: Prospects and Paradigms
cocited    15      2  0.078         -  doi:10.1145/3442188.3445922              On the Dangers of Stochastic Parrots
citer       1         0.202         -  doi:10.1111/caim.70013                   Switching Perspectives: Enhancing Generative Artificial Intelligence's
citer       2         0.180         -  doi:10.2139/ssrn.5013086                 How Experience Moderates the Impact of Generative AI Ideas on the Rese
citer       3         0.122         -  doi:10.1007/s11186-026-09753-4           The rebirth of the author: writing critical social theory in the time 
citer       4         0.117         -  doi:10.1080/10401334.2026.2737803        From Solitude to AI Companionship—Three Phases of a Writing Life and W
citer       5         0.115         -  doi:10.1017/s0267190525000042            Digital accents, homogeneity-by-design, and the evolving social scienc
citer       6         0.091         -  doi:10.1145/3746175.3746199              Bridging the conceptual gap between workers and data-scientists' needs
citer       7         0.081         -  doi:10.1080/21620555.2026.2707167        Vibe researching: can AI agents with skills replace or augment social 
citer       8         0.026         -  doi:10.1038/d41586-026-00665-y           AI agents are ‘aeroplanes for the mind’: five ways to ensure that scie
citer       9         0.023         -  doi:10.2139/ssrn.5169619                 A Quest for AI Knowledge
citer      10         0.022         -  doi:10.1007/978-3-032-32152-7_4          AI and Wicked Problems
citer      11         0.020         -  doi:10.1007/s13347-026-01214-1           The Artificial View from Somewhere: Or How AI Could Undermine Scientif
citer      12         0.015         -  doi:10.1002/qub2.70032                   Conversing with machines: How AI is changing the way scientists think
```

---

## [2026-11-02 08:48 UTC] Step 35 — v1b 共被引的敏感性检查：引用者改按数据与方法面过滤

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b --cocite --citer-filter '("science of science" OR bibliometric*)' --label C3
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

citing works: 1083 cite the seeds; 10 pass the filter '("science of science" OR bibliometrics)'; 0 letters/replies excluded; 10 citers used
co-cited: 596 works cited by the citers; 10 cited by at least 2
already in search results (results/merged/merged_v1b.json): 0
written: results/raw/chase_C3_v1b.json, results/merged/chase_C3_v1b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      4  0.020         -  doi:10.1016/j.jbusres.2021.04.070        How to conduct a bibliometric analysis: An overview and guidelines
cocited     2      4  0.030         -  doi:10.1007/s11192-009-0146-3            Software survey: VOSviewer, a computer program for bibliometric mappin
cocited     3      3  0.020         -  doi:10.1016/j.joi.2017.08.007            bibliometrix : An R-tool for comprehensive science mapping analysis
cocited     4      3  0.021         -  doi:10.1136/bmj.n71                      The PRISMA 2020 statement: an updated guideline for reporting systemat
cocited     5      2  0.140         -  doi:10.1080/10400419.2025.2587803        Agency in Human-AI Collaboration for Image Generation and Creative Wri
cocited     6      2  0.038         -  doi:10.1038/s41562-024-02020-5           Quantifying the use and potential benefits of artificial intelligence 
cocited     7      2  0.091         -  doi:10.1080/10400419.2022.2107850        Redefining Creativity in the Era of AI? Perspectives of Computer Scien
cocited     8      2  0.078         -  doi:10.1016/j.respol.2022.104604         Artificial intelligence in science: An emerging general method of inve
cocited     9      2  0.200         -  doi:10.1093/pnasnexus/pgae052            Generative artificial intelligence, human creativity, and art
cocited    10      2  0.110         -  doi:10.3390/arts8010026                  Art, Creativity, and the Potential of Artificial Intelligence
citer       1         0.107         -  doi:10.1002/pchj.70042                   Artificial Intelligence Reshapes Creativity: A Multidimensional Evalua
citer       2         0.105         -  doi:10.1108/ijem-10-2024-0653            Generative artificial intelligence for management education: applicati
citer       3         0.103         -  doi:10.1016/j.infsof.2026.108277         How reliance on GenAI might limit human creativity and critical thinki
citer       4         0.093         -  doi:10.66815/ejecs/3311                  Artificial Intelligence-Supported Cultural Art Practices: A Bibliometr
citer       5         0.089         -  doi:10.1007/s44163-025-00760-5           GenAI: a scientometric analysis of research trends using biblioshiny a
citer       6         0.078         -  doi:10.3390/info17090893                 Ownership-Preserving Autonomy in Creative Human–Robot Interaction: A S
citer       7         0.073         -  doi:10.1177/20552076261499911            AI’s impact on medical research: A bibliometric study of citation impa
citer       8         0.064         -  doi:10.1016/j.ssaho.2026.103470          Creativity skills in entrepreneurship education: A bibliometric analys
citer       9         0.053         -  doi:10.1007/s11366-026-09932-1           Innovation and Diffusion: The Effects of AI Integration on Knowledge D
citer      10         0.028         -  doi:10.1080/14480220.2026.2630822        Digital skills integration and EV technician training: mapping core co
```

---

## [2026-11-02 08:49 UTC] Step 36 — v2b 检索式（v2 检索式中含 narrowing 的 Q2、Q3、Q6 加 AND NOT ("narrow AI" OR "narrow artificial intelligence")）语法检查

**命令**

```bash
python3 scripts/search.py --queries queries/queries_v2b.json --dry-run
```

**输出**（退出码 0）

```
Q1 [component]
  openalex:        ("large language models" OR "generative AI") AND (homogenization OR homogenisation OR "algorithmic monoculture" OR "collective diversity")
  semanticscholar: ("large language models" | "generative AI") + (homogeniz* | homogenis* | "algorithmic monoculture" | "collective diversity")
Q2 [component]
  openalex:        (narrowing OR "topic diversity" OR "topic concentration" OR "research diversification") AND (economists OR "economic research" OR "management research" OR "business research") AND NOT ("narrow AI" OR "narrow artificial intelligence")
  semanticscholar: (narrowing | "topic diversity" | "topic concentration" | "research diversification") + (economist* | "economic research" | "management research" | "business research") + -("narrow AI" | "narrow artificial intelligence")
Q3 [application]
  openalex:        ("artificial intelligence" OR "AI tools" OR "generative AI" OR "large language models") AND (narrowing OR "topic diversity" OR "topic concentration" OR "collective diversity" OR "research topic selection") AND scientists AND NOT ("narrow AI" OR "narrow artificial intelligence")
  semanticscholar: ("artificial intelligence" | "AI tools" | "generative AI" | "large language models") + (narrowing | "topic diversity" | "topic concentration" | "collective diversity" | "research topic selection") + scientist* + -("narrow AI" | "narrow artificial intelligence")
Q4 [application]
  openalex:        ("streetlight effect" OR "Matthew effect" OR "exploration-exploitation") AND ("artificial intelligence" OR "AI tools" OR "generative AI" OR "large language models") AND (economists OR "economic research" OR "management research" OR "business research")
  semanticscholar: ("streetlight effect" | "Matthew effect" | "exploration-exploitation") + ("artificial intelligence" | "AI tools" | "generative AI" | "large language models") + (economist* | "economic research" | "management research" | "business research")
Q5 [method]
  openalex:        ("LLM-generated text" OR "topic modeling" OR "difference-in-differences") AND ("science of science" OR bibliometrics) AND ("large language models" OR "generative AI")
  semanticscholar: ("LLM-generated text" | "topic modeling" | "difference-in-differences") + ("science of science" | bibliometric*) + ("large language models" | "generative AI")
Q6 [concurrent]
  openalex:        ("artificial intelligence" OR "AI tools" OR "generative AI" OR "large language models") AND (narrowing OR "topic diversity" OR "topic concentration" OR "collective diversity" OR "research diversification" OR "research topic selection") AND (economists OR "economic research" OR "management research" OR "business research") AND NOT ("narrow AI" OR "narrow artificial intelligence")
  semanticscholar: ("artificial intelligence" | "AI tools" | "generative AI" | "large language models") + (narrowing | "topic diversity" | "topic concentration" | "collective diversity" | "research diversification" | "research topic selection") + (economist* | "economic research" | "management research" | "business research") + -("narrow AI" | "narrow artificial intelligence")

6/6 queries valid (dry run, nothing sent)
```

---

## [2026-11-02 08:49 UTC] Step 37 — v2b 检索（v2b 检索式；S2 本地重排）

**命令**

```bash
python3 scripts/search.py --queries queries/queries_v2b.json --suffix _v2b
```

**输出**（退出码 0）

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex               785    25     0  results/raw/openalex_Q1_v2b.json
Q1    component   semanticscholar        392    25     1  results/raw/semanticscholar_Q1_v2b.json
Q2    component   openalex              2756    25     5  results/raw/openalex_Q2_v2b.json
Q2    component   semanticscholar       2160    25     5  results/raw/semanticscholar_Q2_v2b.json
Q3    application openalex               247    25     0  results/raw/openalex_Q3_v2b.json
Q3    application semanticscholar        111    25     0  results/raw/semanticscholar_Q3_v2b.json
Q4    application openalex                 3     3     0  results/raw/openalex_Q4_v2b.json
Q4    application semanticscholar          0     0     0  results/raw/semanticscholar_Q4_v2b.json
Q5    method      openalex                50    25     0  results/raw/openalex_Q5_v2b.json
Q5    method      semanticscholar         45    25     1  results/raw/semanticscholar_Q5_v2b.json
Q6    concurrent  openalex                39    25     1  results/raw/openalex_Q6_v2b.json  [year>=2023]
Q6    concurrent  semanticscholar          6     6     0  results/raw/semanticscholar_Q6_v2b.json  [year>=2023]

12/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25: OpenAlex by API relevance, S2 re-ranked locally by relevance); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
```

---

## [2026-11-02 08:50 UTC] Step 38 — v2b 检索质量检查

**命令**

```bash
python3 scripts/qa.py --suffix _v2b
```

**输出**（退出码 0）

```
file                                  n abstract  conform (all)  conform (with abstract)
openalex_Q1_v2b.json                 25       20   25/25 (100%)             20/20 (100%)
openalex_Q2_v2b.json                 25       20    22/25 (88%)             20/20 (100%)
openalex_Q3_v2b.json                 25       20    20/25 (80%)             20/20 (100%)
openalex_Q4_v2b.json                  3        3     3/3 (100%)               3/3 (100%)
openalex_Q5_v2b.json                 25       21    21/25 (84%)             21/21 (100%)
openalex_Q6_v2b.json                 25       19    18/25 (72%)              18/19 (95%)
semanticscholar_Q1_v2b.json          25       23   25/25 (100%)             23/23 (100%)
semanticscholar_Q2_v2b.json          25        5     9/25 (36%)               5/5 (100%)
semanticscholar_Q3_v2b.json          25       24    24/25 (96%)             24/24 (100%)
semanticscholar_Q4_v2b.json           0        0            0/0                      0/0
semanticscholar_Q5_v2b.json          25       23    24/25 (96%)             23/23 (100%)
semanticscholar_Q6_v2b.json           6        6     6/6 (100%)               6/6 (100%)

total: 197/234 records conform; among records with an abstract: 183/184  (Porter approximation of the APIs' KStem-like matching)
```

---

## [2026-11-02 08:50 UTC] Step 39 — v2b 合并去重与排序（默认方法）

**命令**

```bash
python3 scripts/merge.py --suffix _v2b
```

**输出**（退出码 0）

```
inputs:     12 files, 234 raw records
merged:     189 works (duplicates removed: 45; groups linked as versions by title: 7; pairs flagged for review: 30)
  version link  M083: openalex_Q1_v2b#3 + openalex_Q1_v2b#9
  version link  M109: openalex_Q1_v2b#8 + openalex_Q1_v2b#14
  version link  M107: openalex_Q1_v2b#10 + openalex_Q1_v2b#18
  version link  M030: openalex_Q2_v2b#2 + semanticscholar_Q2_v2b#6
  version link  M006: openalex_Q3_v2b#1 + openalex_Q3_v2b#3
  version link  M002: openalex_Q3_v2b#11 + openalex_Q3_v2b#12
  version link  M010: openalex_Q5_v2b#13 + openalex_Q5_v2b#14
  review        M017 / M101: same title, but two different non-preprint DOIs
  review        M032 / M065: same title, but one record has a data-repository DOI
  review        M168 / M169: same title, but two different non-preprint DOIs
  review        M168 / M162: same title, but two different non-preprint DOIs
  review        M168 / M163: same title, but two different non-preprint DOIs
  review        M168 / M164: same title, but two different non-preprint DOIs
  review        M168 / M165: same title, but two different non-preprint DOIs
  review        M168 / M166: same title, but two different non-preprint DOIs
  review        M168 / M170: near-identical titles (ratio 0.88, word Jaccard 0.68)
  review        M169 / M162: same title, but two different non-preprint DOIs
  review        M169 / M163: same title, but two different non-preprint DOIs
  review        M169 / M164: same title, but two different non-preprint DOIs
  review        M169 / M165: same title, but two different non-preprint DOIs
  review        M169 / M166: same title, but two different non-preprint DOIs
  review        M169 / M170: near-identical titles (ratio 0.88, word Jaccard 0.68)
  review        M162 / M163: same title, but two different non-preprint DOIs
  review        M162 / M164: same title, but two different non-preprint DOIs
  review        M162 / M165: same title, but two different non-preprint DOIs
  review        M162 / M166: same title, but two different non-preprint DOIs
  review        M162 / M170: near-identical titles (ratio 0.88, word Jaccard 0.68)
  review        M163 / M164: same title, but two different non-preprint DOIs
  review        M163 / M165: same title, but two different non-preprint DOIs
  review        M163 / M166: same title, but two different non-preprint DOIs
  review        M163 / M170: near-identical titles (ratio 0.88, word Jaccard 0.68)
  review        M164 / M165: same title, but two different non-preprint DOIs
  review        M164 / M166: same title, but two different non-preprint DOIs
  review        M164 / M170: near-identical titles (ratio 0.88, word Jaccard 0.68)
  review        M165 / M166: same title, but two different non-preprint DOIs
  review        M165 / M170: near-identical titles (ratio 0.88, word Jaccard 0.68)
  review        M166 / M170: near-identical titles (ratio 0.88, word Jaccard 0.68)
id_status:  DOI 155 | arXiv 22 | UNVERIFIED 12
sources:    openalex only 85 | semanticscholar only 74 | both 30
per query:  Q1 39 | Q2 46 | Q3 38 | Q4 3 | Q5 41 | Q6 24
written:    results/merged/merged_v2b.json, results/merged/candidates_v2b.csv (top 20; sorted by RRF, then BM25)
cutoff:     works sharing the #20 score (RRF and BM25): 1

rank  id        rrf   bm25 conf hits year  identifier                               title
   1  M001   0.0462  13.72    2    3 2024  doi:10.48550/arxiv.2409.15626            Qualitative Insights Tool (QualIT): LLM Enhanced Topic Mod…
   2  M031   0.0328   5.00    1    2 1998  doi:10.1057/palgrave.jibs.8490055        Cognitive Tendencies in International Business Research: I…
   3  M006   0.0325   9.76    1    2 2026  doi:10.1038/s41586-025-09922-y           Artificial intelligence tools expand scientists’ impact bu…
   4  M025   0.0320   6.37    1    2 2024  doi:10.22318/icls2024.259570             Learning About and Against Generative AI Through Mapping G…
   5  M024   0.0318   9.01    1    2 2024  doi:10.1126/sciadv.adn5290               Generative AI enhances individual creativity but reduces t…
   6  M030   0.0313   7.67    1    2 2004  UNVERIFIED                               WHAT ECONOMISTS DO: TRENDS IN ECONOMIC RESEARCH
   7  M029   0.0313   5.29    1    2 2008  doi:10.5465/amj.2008.34789630            From the Editors Beyond Contextualization: Using Context T…
   8  M004   0.0311   7.07    1    2 2026  doi:10.32599/apjb.17.1.202603.1          Analysis of Generative AI Research Trends in Korean Busine…
   9  M022   0.0311   7.75    1    2 2025  doi:10.1016/j.caeai.2025.100456          Unveiling the dynamics of generative AI adoption: A busine…
  10  M026   0.0310   9.56    1    2 2022  doi:10.1088/2632-2153/ac61eb             ARTS: autonomous research topic selection system using wor…
  11  M002   0.0302   7.12    3    2 2024  doi:10.1017/9781009483094.004            Artificial Intelligence and the Economics of Decision-Maki…
  12  M013   0.0302   5.80    2    2 2026  doi:10.1111/joes.70175                   Regulating the Artificial Intelligence Economy: A Systemat…
  13  M023   0.0302   4.60    2    2 2024  doi:10.6018/turismo.616471               CYBERSECURITY IN TOURISM AND HOSPITALITY MANAGEMENT RESEAR…
  14  M007   0.0301   4.37    2    2 2026  doi:10.63313/ebm.9154                    Artificial Intelligence-Embedded Restructuring of Enterpri…
  15  M008   0.0299   9.90    1    2 2026  doi:10.56831/psen-08-274                 Does Generative AI Stifle Creativity? Convergence and Homo…
  16  M028   0.0294   4.17    0    2 2010  doi:10.1016/j.jbusres.2010.11.005        Where does business research go from here? Food-for-though…
  17  M005   0.0293  11.24    1    2 2026  doi:10.37630/bijee.v4i1.4446             Artificial Intelligence in English Language Teaching (2018…
  18  M020   0.0292   4.20    1    2 2025  doi:10.48550/arxiv.2504.12317            Large language models reshape the language of science
  19  M003   0.0289  15.21    1    2 2026  doi:10.71097/ijsat.v17.i1.10159          AI Tools in Scientific Research: Boosting Individuals at t…
  20  M015   0.0288   4.59    2    2 2026  doi:10.3390/computers15100689            Toward AI-Enabled Process Model Selection for IT Projects:…
```

---

## [2026-11-02 08:52 UTC] Step 40 — 修正：S2 前 25 条中同题记录只留一条；待核对按组显示

**发现**（Step 37、39）：v2b 的 S2 Q2 本地重排后，前 25 条中有 8 条是 Organization Studies 在多期重复刊登的同一份征稿启事（"Call for Papers Special Issue on Advancing Organization Studies in Family Business Research…"，每期一个 DOI，如 10.1177/0170840615588740a），占去 8 个名额；merge.py 把它们两两列为待核对，共 28 对。

**做了什么**

- `scripts/search.py` 的 S2 本地重排：标题完全相同的记录只保留排在最前的一条，被去掉的条数记在保留记录的 `local_rank.same_title_dropped` 和 meta 的 `pool.same_title_dropped` 中（只影响前 25 条的选取，不影响 API 报告的命中数）。
- `scripts/merge.py`：终端输出把两两的待核对关系并成组显示；merged.json 中仍保留全部两两关系。
- 新增测试（同题只留一条）；`python3 -W error::ResourceWarning -m unittest discover -s tests` → Ran 45 tests … OK。

Step 29–39 的 v1b、v2b 结果作废，下面用修正后的流程从检索开始重跑，输出覆盖同名文件。

**产出文件**：`scripts/search.py`、`scripts/merge.py`、`tests/test_pipeline.py`（修改）

---

## [2026-11-02 08:52 UTC] Step 41 — v1b 重跑检索（修正后的流程）

**命令**

```bash
python3 scripts/search.py --queries queries/queries.json --suffix _v1b
```

**输出**（退出码 0）

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex               785    25     0  results/raw/openalex_Q1_v1b.json
Q1    component   semanticscholar        392    25     1  results/raw/semanticscholar_Q1_v1b.json
Q2    component   openalex                38    25     0  results/raw/openalex_Q2_v1b.json
Q2    component   semanticscholar         43    25     1  results/raw/semanticscholar_Q2_v1b.json
Q3    application openalex                 8     8     1  results/raw/openalex_Q3_v1b.json
Q3    application semanticscholar          9     9     0  results/raw/semanticscholar_Q3_v1b.json
Q4    application openalex                 1     1     0  results/raw/openalex_Q4_v1b.json
Q4    application semanticscholar          1     1     0  results/raw/semanticscholar_Q4_v1b.json
Q5    method      openalex                50    25     0  results/raw/openalex_Q5_v1b.json
Q5    method      semanticscholar         45    25     1  results/raw/semanticscholar_Q5_v1b.json
Q6    concurrent  openalex                63    25     1  results/raw/openalex_Q6_v1b.json  [year>=2023]
Q6    concurrent  semanticscholar         23    22     1  results/raw/semanticscholar_Q6_v1b.json  [year>=2023]

12/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25: OpenAlex by API relevance, S2 re-ranked locally by relevance); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
```

---

## [2026-11-02 08:53 UTC] Step 42 — v1b 检索质量检查

**命令**

```bash
python3 scripts/qa.py --suffix _v1b
```

**输出**（退出码 0）

```
file                                  n abstract  conform (all)  conform (with abstract)
openalex_Q1_v1b.json                 25       20   25/25 (100%)             20/20 (100%)
openalex_Q2_v1b.json                 25       16    16/25 (64%)             16/16 (100%)
openalex_Q3_v1b.json                  8        7      7/8 (88%)               7/7 (100%)
openalex_Q4_v1b.json                  1        0       0/1 (0%)                      0/0
openalex_Q5_v1b.json                 25       21    21/25 (84%)             21/21 (100%)
openalex_Q6_v1b.json                 25       23    22/25 (88%)              22/23 (96%)
semanticscholar_Q1_v1b.json          25       23   25/25 (100%)             23/23 (100%)
semanticscholar_Q2_v1b.json          25       21    21/25 (84%)             21/21 (100%)
semanticscholar_Q3_v1b.json           9        7      4/9 (44%)                4/7 (57%)
semanticscholar_Q4_v1b.json           1        0       0/1 (0%)                      0/0
semanticscholar_Q5_v1b.json          25       23    24/25 (96%)             23/23 (100%)
semanticscholar_Q6_v1b.json          22       20    17/22 (77%)              17/20 (85%)

total: 182/216 records conform; among records with an abstract: 174/181  (Porter approximation of the APIs' KStem-like matching)
```

---

## [2026-11-02 08:53 UTC] Step 43 — v1b 合并去重与排序（默认方法）

**命令**

```bash
python3 scripts/merge.py --suffix _v1b
```

**输出**（退出码 0）

```
inputs:     12 files, 216 raw records
merged:     164 works (duplicates removed: 52; groups linked as versions by title: 6; pairs flagged for review: 2 in 2 cluster(s))
  version link  M089: openalex_Q1_v1b#3 + openalex_Q1_v1b#9
  version link  M112: openalex_Q1_v1b#8 + openalex_Q1_v1b#14
  version link  M111: openalex_Q1_v1b#10 + openalex_Q1_v1b#18
  version link  M142: openalex_Q2_v1b#9 + openalex_Q2_v1b#11
  version link  M008: openalex_Q5_v1b#13 + openalex_Q5_v1b#14
  version link  M072: openalex_Q6_v1b#12 + openalex_Q6_v1b#13
  review        M018, M103: same title, but two different non-preprint DOIs
  review        M041, M075: same title, but one record has a data-repository DOI
id_status:  DOI 140 | arXiv 18 | UNVERIFIED 6
sources:    openalex only 57 | semanticscholar only 67 | both 40
per query:  Q1 39 | Q2 33 | Q3 12 | Q4 1 | Q5 41 | Q6 38
written:    results/merged/merged_v1b.json, results/merged/candidates_v1b.csv (top 20; sorted by RRF, then BM25)
cutoff:     works sharing the #20 score (RRF and BM25): 1

rank  id        rrf   bm25 conf hits year  identifier                               title
   1  M015   0.0328   0.00    0    2 2025  doi:10.1038/s41586-025-09640-5           A multimodal robotic platform for multi-element electrocat…
   2  M001   0.0320   8.88    1    2 2026  doi:10.1038/s41598-026-54348-9           A temporal adaptive dictionary-constrained LDA and Bi-cali…
   3  M007   0.0318   5.72    1    2 2026  doi:10.1177/01655515261461741            From connectivity to insight: A graph neural network–large…
   4  M026   0.0318   5.64    1    2 2024  doi:10.1126/sciadv.adn5290               Generative AI enhances individual creativity but reduces t…
   5  M031   0.0315   5.22    1    2 2023  doi:10.18559/ebr.2023.2.732              The rise of generative AI and possible effects on the econ…
   6  M002   0.0311   4.68    1    2 2026  doi:10.32599/apjb.17.1.202603.1          Analysis of Generative AI Research Trends in Korean Busine…
   7  M025   0.0311   4.50    1    2 2025  doi:10.1016/j.caeai.2025.100456          Unveiling the dynamics of generative AI adoption: A busine…
   8  M013   0.0310   4.62    1    2 2026  doi:10.48550/arxiv.2606.10587            Towards Diverse Scientific Hypothesis Search with Large La…
   9  M017   0.0310   1.31    0    2 2025  doi:10.1007/s11701-025-03108-4           Bibliometric analysis of robotic-assisted hepatobiliary an…
  10  M011   0.0309   6.16    1    2 2026  doi:10.1111/ssm.70041                    Prompt‐a‐Scientist: Using Generative AI to Disrupt Stereot…
  11  M038   0.0306   5.17    1    2 2018  doi:10.1186/s13643-018-0709-6            Evaluating characteristics of PROSPERO records as predicto…
  12  M040   0.0303   9.55    1    2 1993  doi:10.1109/hicss.1993.270676            Drug design using inductive logic programming
  13  M037   0.0302   4.25    1    2 2018  doi:10.1016/j.ecolmodel.2018.04.020      Bibliometric review of ecological network analysis: 2010–2…
  14  M032   0.0301   4.28    1    2 2022  doi:10.1007/s11769-022-1265-5            Bibliometric Review of Biodiversity Offsetting During 1992…
  15  M006   0.0299   5.11    1    2 2026  doi:10.56831/psen-08-274                 Does Generative AI Stifle Creativity? Convergence and Homo…
  16  M035   0.0296   0.00    0    2 2020  doi:10.1007/978-981-15-1420-3_90         Feature Selection Algorithms in Medical Data Classificatio…
  17  M021   0.0294   4.87    1    2 2025  doi:10.51574/ijrer.v5i1.4271             Make A Match Learning Model on Learning Outcomes in Elemen…
  18  M003   0.0293   4.62    1    2 2026  doi:10.37630/bijee.v4i1.4446             Artificial Intelligence in English Language Teaching (2018…
  19  M034   0.0292   3.69    1    2 2020  doi:10.1080/08911762.2020.1765444        A Systematic Literature Review and Bibliometric Analysis o…
  20  M036   0.0290   4.85    1    2 2020  doi:10.1108/bij-04-2020-0137             Service supply chain: from bibliometric analysis to conten…
```

---

## [2026-11-02 08:53 UTC] Step 44 — v1b 从其他版本补摘要（前 20 篇）

**命令**

```bash
python3 scripts/enrich.py --top 20 --candidates results/merged/candidates_v1b.csv --out evidence/enrichment_v1b.json
```

**输出**（退出码 0）

```
  1 M015  needs=abstract,arxiv_id      versions=0 found=- 
  2 M001  needs=arxiv_id               versions=0 found=- 
  3 M007  needs=arxiv_id               versions=0 found=- 
  4 M026  needs=-                      versions=0 found=- 
  5 M031  needs=arxiv_id               versions=0 found=- 
  6 M002  needs=arxiv_id               versions=0 found=- 
  7 M025  needs=arxiv_id               versions=0 found=- 
  8 M013  needs=-                      versions=0 found=- 
  9 M017  needs=abstract,arxiv_id      versions=0 found=- 
 10 M011  needs=arxiv_id               versions=0 found=- 
 11 M038  needs=arxiv_id               versions=0 found=- 
 12 M040  needs=arxiv_id               versions=0 found=- 
 13 M037  needs=arxiv_id               versions=0 found=- 
 14 M032  needs=arxiv_id               versions=0 found=- 
 15 M006  needs=arxiv_id               versions=0 found=- 
 16 M035  needs=abstract,arxiv_id      versions=0 found=- 
 17 M021  needs=arxiv_id               versions=0 found=- 
 18 M003  needs=arxiv_id               versions=0 found=- 
 19 M034  needs=arxiv_id               versions=0 found=- 
 20 M036  needs=arxiv_id               versions=0 found=- 

missing abstracts: 3 → added from another version: 0; arXiv IDs added: 0; DOIs suggested (verify before use): 0
written: evidence/enrichment_v1b.json
```

---

## [2026-11-02 08:54 UTC] Step 45 — v1b 引文追踪：一步（种子：v1 证据表中至少 2 个面为 overlap 的文献）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

pool: 1171 works linked to the seeds (66 linked to more than one seed)
already in search results (results/merged/merged_v1b.json): 7
written: results/raw/chase_C1_v1b.json, results/merged/chase_C1_v1b.csv

path     rank  score    sim in_search  identifier                               title
onehop      1      2  0.326      M112  doi:10.1016/j.chbah.2025.100207          Homogenizing effect of large language models (LLMs) on creative divers
onehop      2      2  0.279      M133  doi:10.1145/3715928.3737481              How AI Ideas Affect the Creativity, Diversity, and Evolution of Human 
onehop      3      2  0.267         -  doi:10.1145/3706598.3713146              Timing Matters: How Using LLMs at Different Timings Influences Writers
onehop      4      2  0.254         -  doi:10.1016/j.yjoc.2026.100142           Perceived human agency and AI-assisted idea generation
onehop      5      2  0.247         -  doi:10.1145/3803784.3816857              The Role of Human Agency in Human-AI Co-Creativity
onehop      6      2  0.239         -  doi:10.1073/pnas.2504966122              Echoes in AI: Quantifying lack of plot diversity in LLM outputs
onehop      7      2  0.234         -  doi:10.1145/3772318.3791185              Partnering with Generative AI: Experimental Evaluation of Model-Led an
onehop      8      2  0.229         -  doi:10.1016/j.chbah.2026.100289          Diverse AI personas can mitigate the homogenization effect in human-AI
onehop      9      2  0.216         -  doi:10.1145/3706598.3714198              Human Creativity in the Age of LLMs: Randomized Experiments on Diverge
onehop     10      2  0.211      M111  doi:10.1177/00491241251327130            Generative AI Meets Open-Ended Survey Responses: Research Participant 
onehop     11      2  0.211         -  doi:10.1145/3708359.3712094              One Does Not Simply Meme Alone: Evaluating Co-Creativity Between LLMs 
onehop     12      2  0.209         -  doi:10.1016/j.tsc.2025.101870            Large language models show both individual and collective creativity c
onehop     13      2  0.207         -  doi:10.1016/j.tsc.2025.101958            Evaluating AI-assisted creative ideation: A crossover study in higher 
onehop     14      2  0.194         -  doi:10.1145/3746175.3746189              Has AI Surpassed Humans in Creative Idea Generation? A Meta-Analysis
onehop     15      2  0.185         -  doi:10.1038/s41562-025-02331-1           A large-scale comparison of divergent creativity in humans and large l
onehop     16      2  0.172         -  doi:10.1057/s41599-025-05867-9           Inspiration booster or creative fixation? The dual mechanisms of LLMs 
onehop     17      2  0.166         -  doi:10.1145/3698061.3726910              From Pen to Prompt: How Creative Writers Integrate AI into their Writi
onehop     18      2  0.159         -  doi:10.1080/17501229.2026.2678315        When LLMs meet creativity: rethinking GFL writing through Human–LLM co
onehop     19      2  0.158         -  doi:10.55737/tk/v5i1.51147               Students’ Creativity, Originality, and Use of Generative AI in Irish A
onehop     20      2  0.152         -  doi:10.1145/3772318.3791329              Decoupling of Usefulness and Novelty: Evaluating the Impact of Generat
```

---

## [2026-11-02 08:54 UTC] Step 46 — v1b 引文追踪：两步共被引（引用者按 v1 研究情境面的使用者一词 scientist* 过滤）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b --cocite --citer-filter 'scientist*'
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

citing works: 1083 cite the seeds; 13 pass the filter 'scientists'; 1 letters/replies excluded; 12 citers used
co-cited: 558 works cited by the citers; 15 cited by at least 2
already in search results (results/merged/merged_v1b.json): 0
written: results/raw/chase_C2_v1b.json, results/merged/chase_C2_v1b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      5  0.040         -  doi:10.1038/s41586-025-09922-y           Artificial intelligence tools expand scientists’ impact but contract s
cocited     2      3  0.112         -  doi:10.1038/s43588-025-00906-6           SciSciGPT: advancing human–AI collaboration in the science of science
cocited     3      3  0.030         -  doi:10.1038/s41562-024-02020-5           Quantifying the use and potential benefits of artificial intelligence 
cocited     4      3  0.085         -  doi:10.3390/soc15010006                  AI Tools in Society: Impacts on Cognitive Offloading and the Future of
cocited     5      3  0.093         -  doi:10.1126/science.adh2586              Experimental evidence on the productivity effects of generative artifi
cocited     6      2  0.177         -  doi:10.1145/3614419.3644000              The Role of Interface Design on Prompt-mediated Creativity in Generati
cocited     7      2  0.263         -  doi:10.48550/arxiv.2409.04109            Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with
cocited     8      2  0.354         -  doi:10.2139/ssrn.4526071                 AI and Its Impact on Creativity and Diversity: An Empirical Study of L
cocited     9      2  0.213         -  doi:10.1038/s41598-023-40858-3           Best humans still outperform artificial intelligence in a creative div
cocited    10      2  0.158         -  doi:10.1073/pnas.2314021121              Can Generative AI improve social science?
cocited    11      2  0.056         -  doi:10.1287/orsc.2021.1549               To Engage or Not to Engage with AI for Critical Judgments: How Profess
cocited    12      2  0.018         -  doi:10.1038/s41586-024-07146-0           Artificial intelligence and illusions of understanding in scientific r
cocited    13      2  0.028         -  doi:10.2139/ssrn.4573321                 Navigating the Jagged Technological Frontier: Field Experimental Evide
cocited    14      2  0.127         -  doi:10.1017/cbo9780511807916.003         The Concept of Creativity: Prospects and Paradigms
cocited    15      2  0.078         -  doi:10.1145/3442188.3445922              On the Dangers of Stochastic Parrots
citer       1         0.202         -  doi:10.1111/caim.70013                   Switching Perspectives: Enhancing Generative Artificial Intelligence's
citer       2         0.180         -  doi:10.2139/ssrn.5013086                 How Experience Moderates the Impact of Generative AI Ideas on the Rese
citer       3         0.122         -  doi:10.1007/s11186-026-09753-4           The rebirth of the author: writing critical social theory in the time 
citer       4         0.117         -  doi:10.1080/10401334.2026.2737803        From Solitude to AI Companionship—Three Phases of a Writing Life and W
citer       5         0.115         -  doi:10.1017/s0267190525000042            Digital accents, homogeneity-by-design, and the evolving social scienc
citer       6         0.091         -  doi:10.1145/3746175.3746199              Bridging the conceptual gap between workers and data-scientists' needs
citer       7         0.081         -  doi:10.1080/21620555.2026.2707167        Vibe researching: can AI agents with skills replace or augment social 
citer       8         0.026         -  doi:10.1038/d41586-026-00665-y           AI agents are ‘aeroplanes for the mind’: five ways to ensure that scie
citer       9         0.023         -  doi:10.2139/ssrn.5169619                 A Quest for AI Knowledge
citer      10         0.022         -  doi:10.1007/978-3-032-32152-7_4          AI and Wicked Problems
citer      11         0.020         -  doi:10.1007/s13347-026-01214-1           The Artificial View from Somewhere: Or How AI Could Undermine Scientif
citer      12         0.015         -  doi:10.1002/qub2.70032                   Conversing with machines: How AI is changing the way scientists think
```

---

## [2026-11-02 08:54 UTC] Step 47 — v1b 共被引的敏感性检查：引用者改按数据与方法面过滤

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b --cocite --citer-filter '("science of science" OR bibliometric*)' --label C3
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

citing works: 1083 cite the seeds; 10 pass the filter '("science of science" OR bibliometrics)'; 0 letters/replies excluded; 10 citers used
co-cited: 596 works cited by the citers; 10 cited by at least 2
already in search results (results/merged/merged_v1b.json): 0
written: results/raw/chase_C3_v1b.json, results/merged/chase_C3_v1b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      4  0.020         -  doi:10.1016/j.jbusres.2021.04.070        How to conduct a bibliometric analysis: An overview and guidelines
cocited     2      4  0.030         -  doi:10.1007/s11192-009-0146-3            Software survey: VOSviewer, a computer program for bibliometric mappin
cocited     3      3  0.020         -  doi:10.1016/j.joi.2017.08.007            bibliometrix : An R-tool for comprehensive science mapping analysis
cocited     4      3  0.021         -  doi:10.1136/bmj.n71                      The PRISMA 2020 statement: an updated guideline for reporting systemat
cocited     5      2  0.140         -  doi:10.1080/10400419.2025.2587803        Agency in Human-AI Collaboration for Image Generation and Creative Wri
cocited     6      2  0.038         -  doi:10.1038/s41562-024-02020-5           Quantifying the use and potential benefits of artificial intelligence 
cocited     7      2  0.091         -  doi:10.1080/10400419.2022.2107850        Redefining Creativity in the Era of AI? Perspectives of Computer Scien
cocited     8      2  0.078         -  doi:10.1016/j.respol.2022.104604         Artificial intelligence in science: An emerging general method of inve
cocited     9      2  0.200         -  doi:10.1093/pnasnexus/pgae052            Generative artificial intelligence, human creativity, and art
cocited    10      2  0.110         -  doi:10.3390/arts8010026                  Art, Creativity, and the Potential of Artificial Intelligence
citer       1         0.107         -  doi:10.1002/pchj.70042                   Artificial Intelligence Reshapes Creativity: A Multidimensional Evalua
citer       2         0.105         -  doi:10.1108/ijem-10-2024-0653            Generative artificial intelligence for management education: applicati
citer       3         0.103         -  doi:10.1016/j.infsof.2026.108277         How reliance on GenAI might limit human creativity and critical thinki
citer       4         0.093         -  doi:10.66815/ejecs/3311                  Artificial Intelligence-Supported Cultural Art Practices: A Bibliometr
citer       5         0.089         -  doi:10.1007/s44163-025-00760-5           GenAI: a scientometric analysis of research trends using biblioshiny a
citer       6         0.078         -  doi:10.3390/info17090893                 Ownership-Preserving Autonomy in Creative Human–Robot Interaction: A S
citer       7         0.073         -  doi:10.1177/20552076261499911            AI’s impact on medical research: A bibliometric study of citation impa
citer       8         0.064         -  doi:10.1016/j.ssaho.2026.103470          Creativity skills in entrepreneurship education: A bibliometric analys
citer       9         0.053         -  doi:10.1007/s11366-026-09932-1           Innovation and Diffusion: The Effects of AI Integration on Knowledge D
citer      10         0.028         -  doi:10.1080/14480220.2026.2630822        Digital skills integration and EV technician training: mapping core co
```

---

## [2026-11-02 08:54 UTC] Step 48 — v2b 重跑检索（修正后的流程；v2b 检索式）

**命令**

```bash
python3 scripts/search.py --queries queries/queries_v2b.json --suffix _v2b
```

**输出**（退出码 0）

```
query purpose     source          total_hits saved no_id  file / note
Q1    component   openalex               785    25     0  results/raw/openalex_Q1_v2b.json
Q1    component   semanticscholar        392    25     1  results/raw/semanticscholar_Q1_v2b.json
Q2    component   openalex              2756    25     5  results/raw/openalex_Q2_v2b.json
Q2    component   semanticscholar       2160    25     7  results/raw/semanticscholar_Q2_v2b.json
Q3    application openalex               247    25     0  results/raw/openalex_Q3_v2b.json
Q3    application semanticscholar        111    25     0  results/raw/semanticscholar_Q3_v2b.json
Q4    application openalex                 3     3     0  results/raw/openalex_Q4_v2b.json
Q4    application semanticscholar          0     0     0  results/raw/semanticscholar_Q4_v2b.json
Q5    method      openalex                50    25     0  results/raw/openalex_Q5_v2b.json
Q5    method      semanticscholar         45    25     1  results/raw/semanticscholar_Q5_v2b.json
Q6    concurrent  openalex                39    25     1  results/raw/openalex_Q6_v2b.json  [year>=2023]
Q6    concurrent  semanticscholar          6     6     0  results/raw/semanticscholar_Q6_v2b.json  [year>=2023]

12/12 requests succeeded. total_hits = API-reported matches; saved = records kept (top 25: OpenAlex by API relevance, S2 re-ranked locally by relevance); no_id = records with neither DOI nor arXiv ID (to be marked UNVERIFIED).
```

---

## [2026-11-02 08:55 UTC] Step 49 — v2b 检索质量检查

**命令**

```bash
python3 scripts/qa.py --suffix _v2b
```

**输出**（退出码 0）

```
file                                  n abstract  conform (all)  conform (with abstract)
openalex_Q1_v2b.json                 25       20   25/25 (100%)             20/20 (100%)
openalex_Q2_v2b.json                 25       20    22/25 (88%)             20/20 (100%)
openalex_Q3_v2b.json                 25       20    20/25 (80%)             20/20 (100%)
openalex_Q4_v2b.json                  3        3     3/3 (100%)               3/3 (100%)
openalex_Q5_v2b.json                 25       21    21/25 (84%)             21/21 (100%)
openalex_Q6_v2b.json                 25       19    18/25 (72%)              18/19 (95%)
semanticscholar_Q1_v2b.json          25       23   25/25 (100%)             23/23 (100%)
semanticscholar_Q2_v2b.json          25        6    10/25 (40%)               6/6 (100%)
semanticscholar_Q3_v2b.json          25       25   25/25 (100%)             25/25 (100%)
semanticscholar_Q4_v2b.json           0        0            0/0                      0/0
semanticscholar_Q5_v2b.json          25       23    24/25 (96%)             23/23 (100%)
semanticscholar_Q6_v2b.json           6        6     6/6 (100%)               6/6 (100%)

total: 199/234 records conform; among records with an abstract: 185/186  (Porter approximation of the APIs' KStem-like matching)
```

---

## [2026-11-02 08:55 UTC] Step 50 — v2b 合并去重与排序（默认方法）

**命令**

```bash
python3 scripts/merge.py --suffix _v2b
```

**输出**（退出码 0）

```
inputs:     12 files, 234 raw records
merged:     190 works (duplicates removed: 44; groups linked as versions by title: 7; pairs flagged for review: 3 in 3 cluster(s))
  version link  M083: openalex_Q1_v2b#3 + openalex_Q1_v2b#9
  version link  M109: openalex_Q1_v2b#8 + openalex_Q1_v2b#14
  version link  M107: openalex_Q1_v2b#10 + openalex_Q1_v2b#18
  version link  M030: openalex_Q2_v2b#2 + semanticscholar_Q2_v2b#6
  version link  M006: openalex_Q3_v2b#1 + openalex_Q3_v2b#3
  version link  M002: openalex_Q3_v2b#11 + openalex_Q3_v2b#12
  version link  M010: openalex_Q5_v2b#13 + openalex_Q5_v2b#14
  review        M017, M101: same title, but two different non-preprint DOIs
  review        M032, M065: same title, but one record has a data-repository DOI
  review        M166, M167: near-identical titles (ratio 0.88, word Jaccard 0.68)
id_status:  DOI 154 | arXiv 22 | UNVERIFIED 14
sources:    openalex only 85 | semanticscholar only 75 | both 30
per query:  Q1 39 | Q2 46 | Q3 39 | Q4 3 | Q5 41 | Q6 24
written:    results/merged/merged_v2b.json, results/merged/candidates_v2b.csv (top 20; sorted by RRF, then BM25)
cutoff:     works sharing the #20 score (RRF and BM25): 1

rank  id        rrf   bm25 conf hits year  identifier                               title
   1  M001   0.0462  13.69    2    3 2024  doi:10.48550/arxiv.2409.15626            Qualitative Insights Tool (QualIT): LLM Enhanced Topic Mod…
   2  M031   0.0328   5.44    1    2 1998  doi:10.1057/palgrave.jibs.8490055        Cognitive Tendencies in International Business Research: I…
   3  M006   0.0325   9.71    1    2 2026  doi:10.1038/s41586-025-09922-y           Artificial intelligence tools expand scientists’ impact bu…
   4  M025   0.0320   6.32    1    2 2024  doi:10.22318/icls2024.259570             Learning About and Against Generative AI Through Mapping G…
   5  M024   0.0318   9.00    1    2 2024  doi:10.1126/sciadv.adn5290               Generative AI enhances individual creativity but reduces t…
   6  M030   0.0313   7.19    1    2 2004  UNVERIFIED                               WHAT ECONOMISTS DO: TRENDS IN ECONOMIC RESEARCH
   7  M029   0.0313   5.17    1    2 2008  doi:10.5465/amj.2008.34789630            From the Editors Beyond Contextualization: Using Context T…
   8  M004   0.0311   7.09    1    2 2026  doi:10.32599/apjb.17.1.202603.1          Analysis of Generative AI Research Trends in Korean Busine…
   9  M022   0.0311   7.77    1    2 2025  doi:10.1016/j.caeai.2025.100456          Unveiling the dynamics of generative AI adoption: A busine…
  10  M026   0.0310   9.55    1    2 2022  doi:10.1088/2632-2153/ac61eb             ARTS: autonomous research topic selection system using wor…
  11  M002   0.0302   7.06    3    2 2024  doi:10.1017/9781009483094.004            Artificial Intelligence and the Economics of Decision-Maki…
  12  M013   0.0302   5.34    2    2 2026  doi:10.1111/joes.70175                   Regulating the Artificial Intelligence Economy: A Systemat…
  13  M023   0.0302   4.52    2    2 2024  doi:10.6018/turismo.616471               CYBERSECURITY IN TOURISM AND HOSPITALITY MANAGEMENT RESEAR…
  14  M007   0.0301   4.30    2    2 2026  doi:10.63313/ebm.9154                    Artificial Intelligence-Embedded Restructuring of Enterpri…
  15  M008   0.0299   9.93    1    2 2026  doi:10.56831/psen-08-274                 Does Generative AI Stifle Creativity? Convergence and Homo…
  16  M005   0.0293  11.27    1    2 2026  doi:10.37630/bijee.v4i1.4446             Artificial Intelligence in English Language Teaching (2018…
  17  M020   0.0292   4.17    1    2 2025  doi:10.48550/arxiv.2504.12317            Large language models reshape the language of science
  18  M028   0.0292   4.70    0    2 2010  doi:10.1016/j.jbusres.2010.11.005        Where does business research go from here? Food-for-though…
  19  M003   0.0289  15.18    1    2 2026  doi:10.71097/ijsat.v17.i1.10159          AI Tools in Scientific Research: Boosting Individuals at t…
  20  M015   0.0288   4.50    2    2 2026  doi:10.3390/computers15100689            Toward AI-Enabled Process Model Selection for IT Projects:…
```

---

## [2026-11-02 08:55 UTC] Step 51 — v2b 从其他版本补摘要（前 20 篇）

**命令**

```bash
python3 scripts/enrich.py --top 20 --candidates results/merged/candidates_v2b.csv --out evidence/enrichment_v2b.json
```

**输出**（退出码 0）

```
  1 M001  needs=-                      versions=0 found=- 
  2 M031  needs=abstract,arxiv_id      versions=0 found=- 
  3 M006  needs=-                      versions=0 found=- 
  4 M025  needs=arxiv_id               versions=0 found=- 
  5 M024  needs=-                      versions=0 found=- 
  6 M030  needs=arxiv_id,doi           versions=1 found=- 
  7 M029  needs=abstract,arxiv_id      versions=0 found=- 
  8 M004  needs=arxiv_id               versions=0 found=- 
  9 M022  needs=arxiv_id               versions=0 found=- 
 10 M026  needs=arxiv_id               versions=0 found=- 
 11 M002  needs=arxiv_id               versions=1 found=- 
 12 M013  needs=arxiv_id               versions=0 found=- 
 13 M023  needs=arxiv_id               versions=0 found=- 
 14 M007  needs=arxiv_id               versions=0 found=- 
 15 M008  needs=arxiv_id               versions=0 found=- 
 16 M005  needs=arxiv_id               versions=0 found=- 
 17 M020  needs=-                      versions=0 found=- 
 18 M028  needs=abstract,arxiv_id      versions=0 found=- 
 19 M003  needs=arxiv_id               versions=0 found=- 
 20 M015  needs=arxiv_id               versions=0 found=- 

missing abstracts: 3 → added from another version: 0; arXiv IDs added: 0; DOIs suggested (verify before use): 0
written: evidence/enrichment_v2b.json
```

---

## [2026-11-02 08:55 UTC] Step 52 — v2b 引文追踪：一步（种子：v2 证据表中至少 2 个面为 overlap 的文献）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table_v2.md --queries queries/queries_v2b.json --suffix _v2b
```

**输出**（退出码 0）

```
seeds (4):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 3: W7124140759 | refs 57 | cited by [117] | Artificial intelligence tools expand scientists’ impact but contract science’s focus
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation
  rank 8: W7135026029, W4417098922 | refs 54 | cited by [42, 1] | The homogenizing effect of large language models on human expression and thought

pool: 1407 works linked to the seeds (92 linked to more than one seed)
already in search results (results/merged/merged_v2b.json): 6
written: results/raw/chase_C1_v2b.json, results/merged/chase_C1_v2b.csv

path     rank  score    sim in_search  identifier                               title
onehop      1      3  0.262         -  doi:10.1016/j.yjoc.2026.100142           Perceived human agency and AI-assisted idea generation
onehop      2      3  0.226         -  doi:10.1016/j.cobeha.2026.101695         From individual gains to collective risks in human–AI co-creativity
onehop      3      3  0.226      M107  doi:10.1177/00491241251327130            Generative AI Meets Open-Ended Survey Responses: Research Participant 
onehop      4      3  0.152         -  doi:10.1007/s43681-026-01215-y           The meek shall inherit the Earth: personality, empathy, and the human 
onehop      5      3  0.102         -  doi:10.1007/s43681-026-01320-y           The politics of creative attribution: generative artificial intelligen
onehop      6      3  0.077         -  doi:10.1016/j.caeai.2026.100684          Agentivism: a learning theory for the age of artificial intelligence
onehop      7      3  0.023         -  doi:10.1007/s13347-026-01214-1           The Artificial View from Somewhere: Or How AI Could Undermine Scientif
onehop      8      2  0.446         -  doi:10.1016/j.eururo.2026.04.004         Re: Artificial Intelligence Tools Expand Scientists’ Impact but Contra
onehop      9      2  0.324      M109  doi:10.1016/j.chbah.2025.100207          Homogenizing effect of large language models (LLMs) on creative divers
onehop     10      2  0.261         -  doi:10.1145/3803784.3816857              The Role of Human Agency in Human-AI Co-Creativity
onehop     11      2  0.259      M134  doi:10.1145/3715928.3737481              How AI Ideas Affect the Creativity, Diversity, and Evolution of Human 
onehop     12      2  0.253         -  doi:10.1145/3706598.3714198              Human Creativity in the Age of LLMs: Randomized Experiments on Diverge
onehop     13      2  0.239         -  doi:10.1016/j.chbah.2026.100289          Diverse AI personas can mitigate the homogenization effect in human-AI
onehop     14      2  0.233         -  doi:10.1145/3772318.3791185              Partnering with Generative AI: Experimental Evaluation of Model-Led an
onehop     15      2  0.220         -  doi:10.1145/3706598.3713146              Timing Matters: How Using LLMs at Different Timings Influences Writers
onehop     16      2  0.210         -  doi:10.1016/j.tsc.2025.101870            Large language models show both individual and collective creativity c
onehop     17      2  0.209         -  doi:10.1016/j.tsc.2025.101958            Evaluating AI-assisted creative ideation: A crossover study in higher 
onehop     18      2  0.208         -  doi:10.1073/pnas.2504966122              Echoes in AI: Quantifying lack of plot diversity in LLM outputs
onehop     19      2  0.193         -  doi:10.1016/j.respol.2026.105575         How experience moderates the impact of AI suggestions on researchers' 
onehop     20      2  0.185         -  doi:10.1145/3708359.3712094              One Does Not Simply Meme Alone: Evaluating Co-Creativity Between LLMs
```

---

## [2026-11-02 08:56 UTC] Step 53 — v2b 引文追踪：两步共被引（引用者按 v2 研究情境组过滤：经济学与管理学研究者）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table_v2.md --queries queries/queries_v2b.json --suffix _v2b --cocite --citer-filter '(economist* OR "economic research" OR "management research" OR "business research")'
```

**输出**（退出码 0）

```
seeds (4):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 3: W7124140759 | refs 57 | cited by [117] | Artificial intelligence tools expand scientists’ impact but contract science’s focus
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation
  rank 8: W7135026029, W4417098922 | refs 54 | cited by [42, 1] | The homogenizing effect of large language models on human expression and thought

citing works: 1213 cite the seeds; 3 pass the filter '(economists OR "economic research" OR "management research" OR "business research")'; 0 letters/replies excluded; 3 citers used
co-cited: 118 works cited by the citers; 24 cited by at least 2
already in search results (results/merged/merged_v2b.json): 0
written: results/raw/chase_C2_v2b.json, results/merged/chase_C2_v2b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      3  0.110         -  doi:10.1093/qje/qjad055                  Machine Learning as a Tool for Hypothesis Generation
cocited     2      2  0.107         -  doi:10.1177/09637214261419427            The Integration of Explanation and Prediction in Behavioral Science
cocited     3      2  0.144         -  doi:10.1287/orsc.2025.20459              CROSSROADS—Organization Research as an Applied Science: Lessons from F
cocited     4      2  0.068         -  doi:10.1177/01708406251326693            Producing Images and Making Judgement: The ongoing use of epistemic te
cocited     5      2  0.146         -  doi:10.1177/26317877241275113            Beyond the Turing Test: Exploring the implications of generative AI fo
cocited     6      2  0.102         -  doi:10.1145/3722138                      Does AI Prediction Scale to Decision Making?
cocited     7      2  0.138         -  doi:10.1177/10944281251339144            Enhancing Theorization Using Artificial Intelligence: Leveraging Large
cocited     8      2  0.129         -  doi:10.1177/87569728241266938            AI for Management and Organization Research: Examples and Reflections 
cocited     9      2  0.162         -  doi:10.18653/v1/2024.nlp4science-1.10    Hypothesis Generation with Large Language Models
cocited    10      2  0.000         -  doi:10.1038/d41586-026-00969-z           Hallucinated citations are polluting the scientific literature. What c
cocited    11      2  0.159         -  doi:10.1177/26317877241239056            Large Language Models and the Future of Organization Theory
cocited    12      2  0.125         -  doi:10.1287/orsc.2026.ed.v37.n3          More Versus Better: Artificial Intelligence, Incentives, and the Emerg
cocited    13      2  0.152         -  doi:10.1177/10944281251377154            Generative Artificial Intelligence in Qualitative Data Analysis: Analy
cocited    14      2  0.061         -  doi:10.1177/00018392241304403            Resisting the Algorithmic Management of Science: Craft and Community A
cocited    15      2  0.054         -  doi:10.1177/00076503231163286            Efficient, Explicatory, and Equitable: Why Qualitative Researchers Sho
cocited    16      2  0.190         -  doi:10.1287/stsc.2024.0189               Theory Is All You Need: AI, Human Cognition, and Causal Reasoning
cocited    17      2  0.139         -  doi:10.1177/00222429241276529            AI–Human Hybrids for Marketing Research: Leveraging Large Language Mod
cocited    18      2  0.064         -  doi:10.1177/26317877211020328            What Theory Is and Can Be: Forms of Theorizing in Organizational Schol
cocited    19      2  0.078         -  doi:10.1111/jpim.12698                   Artificial intelligence in innovation management: A review of innovati
cocited    20      2  0.065         -  doi:10.1038/s41586-024-08252-9           Probabilistic weather forecasting with machine learning
citer       1         0.132         -  doi:10.1111/emre.70114                   How will AI affect theorizing in management research?
citer       2         0.033         -  doi:10.2139/ssrn.6594299                 Improving Abductive Reasoning
citer       3         0.023         -  doi:10.2139/ssrn.7613938                 How Will AI Affect Theorizing in Management Research?
```

---

## [2026-11-02 08:57 UTC] Step 54 — 修正：引文追踪中同一研究的不同版本只算一次

**发现**（Step 53）：v2b 的共被引只有 3 篇引用者通过过滤，其中 2 篇是同一研究的两个版本（"How will AI affect theorizing in management research?" 的期刊版 doi:10.1111/emre.70114 与 SSRN 版 doi:10.2139/ssrn.7613938），所以大多数"被 2 篇共同引用"其实是同一篇论文算了两次。调研中也提到被引文献的预印本与正式版会把支持数分开（Hao 等 19 对 2）。

**做了什么**（`scripts/snowball.py`）

- 引用者：题目规范化后相同（≥5 词，且不是来信、更正之类）的视为同一研究，参考文献取并集，只算一篇。
- 被引文献：同样按题目合并版本，支持数取引用者组的并集；代表记录优先取正式发表版本，其余版本记在 `chase.versions`。
- 一步模式：同一研究的几个版本合成一行，与种子的关系取并集。
- 测试补充版本合并的情形；`python3 -W error::ResourceWarning -m unittest discover -s tests` → Ran 45 tests … OK。

Step 45–47、52–53 的引文追踪结果作废，下面重跑（检索与合并结果不受影响）。

**产出文件**：`scripts/snowball.py`、`tests/test_pipeline.py`（修改）

---

## [2026-11-02 08:57 UTC] Step 55 — v1b 引文追踪：一步（重跑）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

pool: 1160 works linked to the seeds (66 linked to more than one seed)
already in search results (results/merged/merged_v1b.json): 7
written: results/raw/chase_C1_v1b.json, results/merged/chase_C1_v1b.csv

path     rank  score    sim in_search  identifier                               title
onehop      1      2  0.326      M112  doi:10.1016/j.chbah.2025.100207          Homogenizing effect of large language models (LLMs) on creative divers
onehop      2      2  0.279      M133  doi:10.1145/3715928.3737481              How AI Ideas Affect the Creativity, Diversity, and Evolution of Human 
onehop      3      2  0.267         -  doi:10.1145/3706598.3713146              Timing Matters: How Using LLMs at Different Timings Influences Writers
onehop      4      2  0.254         -  doi:10.1016/j.yjoc.2026.100142           Perceived human agency and AI-assisted idea generation
onehop      5      2  0.247         -  doi:10.1145/3803784.3816857              The Role of Human Agency in Human-AI Co-Creativity
onehop      6      2  0.239         -  doi:10.1073/pnas.2504966122              Echoes in AI: Quantifying lack of plot diversity in LLM outputs
onehop      7      2  0.234         -  doi:10.1145/3772318.3791185              Partnering with Generative AI: Experimental Evaluation of Model-Led an
onehop      8      2  0.229         -  doi:10.1016/j.chbah.2026.100289          Diverse AI personas can mitigate the homogenization effect in human-AI
onehop      9      2  0.216         -  doi:10.1145/3706598.3714198              Human Creativity in the Age of LLMs: Randomized Experiments on Diverge
onehop     10      2  0.211      M111  doi:10.1177/00491241251327130            Generative AI Meets Open-Ended Survey Responses: Research Participant 
onehop     11      2  0.211         -  doi:10.1145/3708359.3712094              One Does Not Simply Meme Alone: Evaluating Co-Creativity Between LLMs 
onehop     12      2  0.209         -  doi:10.1016/j.tsc.2025.101870            Large language models show both individual and collective creativity c
onehop     13      2  0.207         -  doi:10.1016/j.tsc.2025.101958            Evaluating AI-assisted creative ideation: A crossover study in higher 
onehop     14      2  0.194         -  doi:10.1145/3746175.3746189              Has AI Surpassed Humans in Creative Idea Generation? A Meta-Analysis
onehop     15      2  0.185         -  doi:10.1038/s41562-025-02331-1           A large-scale comparison of divergent creativity in humans and large l
onehop     16      2  0.172         -  doi:10.1057/s41599-025-05867-9           Inspiration booster or creative fixation? The dual mechanisms of LLMs 
onehop     17      2  0.166         -  doi:10.1145/3698061.3726910              From Pen to Prompt: How Creative Writers Integrate AI into their Writi
onehop     18      2  0.160         -  doi:10.1080/17501229.2026.2678315        When LLMs meet creativity: rethinking GFL writing through Human–LLM co
onehop     19      2  0.158         -  doi:10.55737/tk/v5i1.51147               Students’ Creativity, Originality, and Use of Generative AI in Irish A
onehop     20      2  0.152         -  doi:10.1145/3772318.3791329              Decoupling of Usefulness and Novelty: Evaluating the Impact of Generat
```

---

## [2026-11-02 08:58 UTC] Step 56 — v1b 引文追踪：两步共被引，引用者按 scientist* 过滤（重跑）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b --cocite --citer-filter 'scientist*'
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

citing works: 1083 cite the seeds; 13 pass the filter 'scientists'; 1 letters/replies excluded; 12 citers used (versions of one work counted once: 0 merged)
co-cited: 558 works cited by the citers; 16 cited by at least 2
already in search results (results/merged/merged_v1b.json): 0
written: results/raw/chase_C2_v1b.json, results/merged/chase_C2_v1b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      5  0.040         -  doi:10.1038/s41586-025-09922-y           Artificial intelligence tools expand scientists’ impact but contract s
cocited     2      3  0.112         -  doi:10.1038/s43588-025-00906-6           SciSciGPT: advancing human–AI collaboration in the science of science
cocited     3      3  0.030         -  doi:10.1038/s41562-024-02020-5           Quantifying the use and potential benefits of artificial intelligence 
cocited     4      3  0.131         -  doi:10.1287/orsc.2025.21838              Navigating the Jagged Technological Frontier: Field Experimental Evide
cocited     5      3  0.084         -  doi:10.3390/soc15010006                  AI Tools in Society: Impacts on Cognitive Offloading and the Future of
cocited     6      3  0.094         -  doi:10.1126/science.adh2586              Experimental evidence on the productivity effects of generative artifi
cocited     7      2  0.176         -  doi:10.1145/3614419.3644000              The Role of Interface Design on Prompt-mediated Creativity in Generati
cocited     8      2  0.266         -  doi:10.48550/arxiv.2409.04109            Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with
cocited     9      2  0.354         -  doi:10.2139/ssrn.4526071                 AI and Its Impact on Creativity and Diversity: An Empirical Study of L
cocited    10      2  0.209         -  doi:10.1038/s41598-023-40858-3           Best humans still outperform artificial intelligence in a creative div
cocited    11      2  0.158         -  doi:10.1073/pnas.2314021121              Can Generative AI improve social science?
cocited    12      2  0.056         -  doi:10.1287/orsc.2021.1549               To Engage or Not to Engage with AI for Critical Judgments: How Profess
cocited    13      2  0.018         -  doi:10.1038/s41586-024-07146-0           Artificial intelligence and illusions of understanding in scientific r
cocited    14      2  0.123         -  doi:10.1017/cbo9780511807916.003         The Concept of Creativity: Prospects and Paradigms
cocited    15      2  0.078         -  doi:10.1145/3442188.3445922              On the Dangers of Stochastic Parrots
cocited    16      2  0.000         -  doi:10.1111/j.1468-0149.1963.tb00813.x   THE STRUCTURE OF SCIENTIFIC REVOLUTIONS
citer       1         0.200         -  doi:10.1111/caim.70013                   Switching Perspectives: Enhancing Generative Artificial Intelligence's
citer       2         0.182         -  doi:10.2139/ssrn.5013086                 How Experience Moderates the Impact of Generative AI Ideas on the Rese
citer       3         0.121         -  doi:10.1007/s11186-026-09753-4           The rebirth of the author: writing critical social theory in the time 
citer       4         0.116         -  doi:10.1017/s0267190525000042            Digital accents, homogeneity-by-design, and the evolving social scienc
citer       5         0.113         -  doi:10.1080/10401334.2026.2737803        From Solitude to AI Companionship—Three Phases of a Writing Life and W
citer       6         0.090         -  doi:10.1145/3746175.3746199              Bridging the conceptual gap between workers and data-scientists' needs
citer       7         0.081         -  doi:10.1080/21620555.2026.2707167        Vibe researching: can AI agents with skills replace or augment social 
citer       8         0.025         -  doi:10.1038/d41586-026-00665-y           AI agents are ‘aeroplanes for the mind’: five ways to ensure that scie
citer       9         0.023         -  doi:10.2139/ssrn.5169619                 A Quest for AI Knowledge
citer      10         0.022         -  doi:10.1007/978-3-032-32152-7_4          AI and Wicked Problems
citer      11         0.020         -  doi:10.1007/s13347-026-01214-1           The Artificial View from Somewhere: Or How AI Could Undermine Scientif
citer      12         0.014         -  doi:10.1002/qub2.70032                   Conversing with machines: How AI is changing the way scientists think
```

---

## [2026-11-02 08:58 UTC] Step 57 — v1b 共被引的敏感性检查：引用者改按数据与方法面过滤（重跑）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --suffix _v1b --cocite --citer-filter '("science of science" OR bibliometric*)' --label C3
```

**输出**（退出码 0）

```
seeds (2):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation

citing works: 1083 cite the seeds; 10 pass the filter '("science of science" OR bibliometrics)'; 0 letters/replies excluded; 10 citers used (versions of one work counted once: 0 merged)
co-cited: 596 works cited by the citers; 10 cited by at least 2
already in search results (results/merged/merged_v1b.json): 0
written: results/raw/chase_C3_v1b.json, results/merged/chase_C3_v1b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      4  0.020         -  doi:10.1016/j.jbusres.2021.04.070        How to conduct a bibliometric analysis: An overview and guidelines
cocited     2      4  0.030         -  doi:10.1007/s11192-009-0146-3            Software survey: VOSviewer, a computer program for bibliometric mappin
cocited     3      3  0.020         -  doi:10.1016/j.joi.2017.08.007            bibliometrix : An R-tool for comprehensive science mapping analysis
cocited     4      3  0.021         -  doi:10.1136/bmj.n71                      The PRISMA 2020 statement: an updated guideline for reporting systemat
cocited     5      2  0.140         -  doi:10.1080/10400419.2025.2587803        Agency in Human-AI Collaboration for Image Generation and Creative Wri
cocited     6      2  0.038         -  doi:10.1038/s41562-024-02020-5           Quantifying the use and potential benefits of artificial intelligence 
cocited     7      2  0.091         -  doi:10.1080/10400419.2022.2107850        Redefining Creativity in the Era of AI? Perspectives of Computer Scien
cocited     8      2  0.078         -  doi:10.1016/j.respol.2022.104604         Artificial intelligence in science: An emerging general method of inve
cocited     9      2  0.200         -  doi:10.1093/pnasnexus/pgae052            Generative artificial intelligence, human creativity, and art
cocited    10      2  0.110         -  doi:10.3390/arts8010026                  Art, Creativity, and the Potential of Artificial Intelligence
citer       1         0.107         -  doi:10.1002/pchj.70042                   Artificial Intelligence Reshapes Creativity: A Multidimensional Evalua
citer       2         0.105         -  doi:10.1108/ijem-10-2024-0653            Generative artificial intelligence for management education: applicati
citer       3         0.103         -  doi:10.1016/j.infsof.2026.108277         How reliance on GenAI might limit human creativity and critical thinki
citer       4         0.093         -  doi:10.66815/ejecs/3311                  Artificial Intelligence-Supported Cultural Art Practices: A Bibliometr
citer       5         0.089         -  doi:10.1007/s44163-025-00760-5           GenAI: a scientometric analysis of research trends using biblioshiny a
citer       6         0.078         -  doi:10.3390/info17090893                 Ownership-Preserving Autonomy in Creative Human–Robot Interaction: A S
citer       7         0.073         -  doi:10.1177/20552076261499911            AI’s impact on medical research: A bibliometric study of citation impa
citer       8         0.064         -  doi:10.1016/j.ssaho.2026.103470          Creativity skills in entrepreneurship education: A bibliometric analys
citer       9         0.053         -  doi:10.1007/s11366-026-09932-1           Innovation and Diffusion: The Effects of AI Integration on Knowledge D
citer      10         0.028         -  doi:10.1080/14480220.2026.2630822        Digital skills integration and EV technician training: mapping core co
```

---

## [2026-11-02 08:58 UTC] Step 58 — v2b 引文追踪：一步（重跑；种子：v2 证据表中至少 2 个面为 overlap 的文献）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table_v2.md --queries queries/queries_v2b.json --suffix _v2b
```

**输出**（退出码 0）

```
seeds (4):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 3: W7124140759 | refs 57 | cited by [117] | Artificial intelligence tools expand scientists’ impact but contract science’s focus
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation
  rank 8: W7135026029, W4417098922 | refs 54 | cited by [42, 1] | The homogenizing effect of large language models on human expression and thought

pool: 1396 works linked to the seeds (92 linked to more than one seed)
already in search results (results/merged/merged_v2b.json): 6
written: results/raw/chase_C1_v2b.json, results/merged/chase_C1_v2b.csv

path     rank  score    sim in_search  identifier                               title
onehop      1      3  0.262         -  doi:10.1016/j.yjoc.2026.100142           Perceived human agency and AI-assisted idea generation
onehop      2      3  0.226         -  doi:10.1016/j.cobeha.2026.101695         From individual gains to collective risks in human–AI co-creativity
onehop      3      3  0.226      M107  doi:10.1177/00491241251327130            Generative AI Meets Open-Ended Survey Responses: Research Participant 
onehop      4      3  0.152         -  doi:10.1007/s43681-026-01215-y           The meek shall inherit the Earth: personality, empathy, and the human 
onehop      5      3  0.102         -  doi:10.1007/s43681-026-01320-y           The politics of creative attribution: generative artificial intelligen
onehop      6      3  0.077         -  doi:10.1016/j.caeai.2026.100684          Agentivism: a learning theory for the age of artificial intelligence
onehop      7      3  0.023         -  doi:10.1007/s13347-026-01214-1           The Artificial View from Somewhere: Or How AI Could Undermine Scientif
onehop      8      2  0.446         -  doi:10.1016/j.eururo.2026.04.004         Re: Artificial Intelligence Tools Expand Scientists’ Impact but Contra
onehop      9      2  0.324      M109  doi:10.1016/j.chbah.2025.100207          Homogenizing effect of large language models (LLMs) on creative divers
onehop     10      2  0.261         -  doi:10.1145/3803784.3816857              The Role of Human Agency in Human-AI Co-Creativity
onehop     11      2  0.259      M134  doi:10.1145/3715928.3737481              How AI Ideas Affect the Creativity, Diversity, and Evolution of Human 
onehop     12      2  0.254         -  doi:10.1145/3706598.3714198              Human Creativity in the Age of LLMs: Randomized Experiments on Diverge
onehop     13      2  0.238         -  doi:10.1016/j.chbah.2026.100289          Diverse AI personas can mitigate the homogenization effect in human-AI
onehop     14      2  0.233         -  doi:10.1145/3772318.3791185              Partnering with Generative AI: Experimental Evaluation of Model-Led an
onehop     15      2  0.221         -  doi:10.1145/3706598.3713146              Timing Matters: How Using LLMs at Different Timings Influences Writers
onehop     16      2  0.210         -  doi:10.1016/j.tsc.2025.101870            Large language models show both individual and collective creativity c
onehop     17      2  0.209         -  doi:10.1016/j.tsc.2025.101958            Evaluating AI-assisted creative ideation: A crossover study in higher 
onehop     18      2  0.208         -  doi:10.1073/pnas.2504966122              Echoes in AI: Quantifying lack of plot diversity in LLM outputs
onehop     19      2  0.193         -  doi:10.1016/j.respol.2026.105575         How experience moderates the impact of AI suggestions on researchers' 
onehop     20      2  0.186         -  doi:10.1145/3708359.3712094              One Does Not Simply Meme Alone: Evaluating Co-Creativity Between LLMs
```

---

## [2026-11-02 08:58 UTC] Step 59 — v2b 引文追踪：两步共被引，引用者按 v2 研究情境组过滤（重跑）

**命令**

```bash
python3 scripts/snowball.py --from-evidence evidence/evidence_table_v2.md --queries queries/queries_v2b.json --suffix _v2b --cocite --citer-filter '(economist* OR "economic research" OR "management research" OR "business research")'
```

**输出**（退出码 0）

```
seeds (4):
  rank 2: W4400578758 | refs 42 | cited by [978] | Generative AI enhances individual creativity but reduces the collective diversity of novel content
  rank 3: W7124140759 | refs 57 | cited by [117] | Artificial intelligence tools expand scientists’ impact but contract science’s focus
  rank 4: W4391556516 | refs 50 | cited by [189] | Homogenization Effects of Large Language Models on Human Creative Ideation
  rank 8: W7135026029, W4417098922 | refs 54 | cited by [42, 1] | The homogenizing effect of large language models on human expression and thought

citing works: 1213 cite the seeds; 3 pass the filter '(economists OR "economic research" OR "management research" OR "business research")'; 0 letters/replies excluded; 2 citers used (versions of one work counted once: 1 merged)
co-cited: 118 works cited by the citers; 1 cited by at least 2
already in search results (results/merged/merged_v2b.json): 0
written: results/raw/chase_C2_v2b.json, results/merged/chase_C2_v2b.csv

path     rank  score    sim in_search  identifier                               title
cocited     1      2  0.121         -  doi:10.1093/qje/qjad055                  Machine Learning as a Tool for Hypothesis Generation
citer       1         0.147         -  doi:10.1111/emre.70114                   How will AI affect theorizing in management research?
citer       2         0.044         -  doi:10.2139/ssrn.6594299                 Improving Abductive Reasoning
```

---

## [2026-11-02 08:59 UTC] Step 60 — 评估：v1 与 v1b 对比（已知文献为参考文献 Hao 等的正式版与预印本）

**命令**

```bash
python3 scripts/compare.py --runs ,_v1b --known 10.1038/s41586-025-09922-y,arXiv:2412.07727 --out results/merged/compare_v1_v1b.json
```

**输出**（退出码 0）

```
                                                    (v1)                  _v1b
ranking method                             hits (legacy)                   RRF
merged works                                         161                   164
works tied at the cutoff                              42                     1
rank of doi:10.1038/s41586-025-099                  None                  None
  in chase lists                                       -         C2/cocited #1
rank of arxiv:2412.07727                            None                  None
  in chase lists                                       -                     -
top10 conform                                          9                     8
top10 noise                                            0                     0
top10 genai                                            5                     8
top10 abstract                                         9                     8
top10 year_median                                 2023.0                2025.5
top10 before_2015                                      1                     0
top20 conform                                         17                    17
top20 noise                                            0                     0
top20 genai                                           11                    10
top20 abstract                                        17                    17
top20 year_median                                 2023.5                2025.0
top20 before_2015                                      1                     1

written: results/merged/compare_v1_v1b.json
```

---

## [2026-11-02 08:59 UTC] Step 61 — 评估：v2 与 v2b 对比（noise 按 Step 15 的定义：只因 narrow AI、narrow applications 等短语才满足检索式）

**命令**

```bash
python3 scripts/compare.py --runs _v2,_v2b --known 10.1038/s41586-025-09922-y,arXiv:2412.07727 --ignore-phrases '"narrow AI"' '"narrow artificial intelligence"' '"narrow applications"' '"narrow systems"' '"narrow-specific tasks"' '"narrow tasks"' --out results/merged/compare_v2_v2b.json
```

**输出**（退出码 0）

```
                                                     _v2                  _v2b
ranking method                             hits (legacy)                   RRF
merged works                                         191                   190
works tied at the cutoff                              32                     1
rank of doi:10.1038/s41586-025-099                     3                     3
  in chase lists                                       -                     -
rank of arxiv:2412.07727                              60                     3
  in chase lists                                       -                     -
top10 conform                                          5                    10
top10 noise                                            4                     0
top10 genai                                            7                     5
top10 abstract                                         9                     8
top10 year_median                                 2024.5                2024.0
top10 before_2015                                      0                     3
top20 conform                                         15                    18
top20 noise                                            4                     1
top20 genai                                           11                     9
top20 abstract                                        18                    17
top20 year_median                                 2024.0                2024.5
top20 before_2015                                      2                     4

written: results/merged/compare_v2_v2b.json
```

---

## [2026-11-02 09:05 UTC] Step 62 — 用改进后的 verify.py 重新核验 v1 证据表（OpenAlex 回退；https 跳转改用 https）

**命令**

```bash
python3 scripts/verify.py
```

**输出**（退出码 0）

```
verify run at 2026-11-02T09:05:14+00:00  table=/home/user/novelty-probe-demo/evidence/evidence_table.md
[1] doi:10.1038/s41586-025-09640-5
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · A multimodal robotic platform for multi-element electrocatalyst discovery
                 registered: Nature | 2025 | journal-article | authors: Zhang; Ren; Hsu
      landing:   302 www.nature.com  -> 落地页 BLOCKED at www.nature.com (network policy, proxy 403)
[2] doi:10.1126/sciadv.adn5290
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the collective diversity of novel content
                 registered: Science Advances | 2024 | journal-article | authors: Doshi; Hauser
      landing:   302 www.science.org  -> 落地页 BLOCKED at www.science.org (network policy, proxy 403)
[3] doi:10.1016/j.ecolmodel.2018.04.020
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · Bibliometric review of ecological network analysis: 2010–2016
                 registered: Ecological Modelling | 2018 | journal-article | authors: Borrett; Sheble; Moody
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[4] doi:10.1145/3635636.3656204
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Homogenization Effects of Large Language Models on Human Creative Ideation
                 registered: Creativity and Cognition | 2024 | proceedings-article | authors: Anderson; Shah; Kreminski
      landing:   302 dl.acm.org  -> 落地页 BLOCKED at dl.acm.org (network policy, proxy 403)
[5] doi:10.1016/j.caeai.2025.100456
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · Unveiling the dynamics of generative AI adoption: A business intelligence analysis through topic modeling-based bibliome…
                 registered: Computers and Education: Artificial Intelligence | 2025 | journal-article | authors: Aldreabi; Alhur; Al-Okaily
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[6] doi:10.1108/ijssp-06-2021-0145
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · Work–life balance: a systematic literature review and bibliometric analysis
                 registered: International Journal of Sociology and Social Policy | 2021 | journal-article | authors: Rashmi; Kataria
      landing:   302 www.emerald.com (http→https)  -> 落地页 BLOCKED at www.emerald.com (network policy, proxy 403)
[7] doi:10.1080/08911762.2020.1765444
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · A Systematic Literature Review and Bibliometric Analysis of Recycling Behavior
                 registered: Journal of Global Marketing | 2020 | journal-article | authors: Phulwani; Kumar; Goyal
      landing:   302 www.tandfonline.com  -> 落地页 BLOCKED at www.tandfonline.com (network policy, proxy 403)
[8] doi:10.1109/hicss.1993.270676
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Drug design using inductive logic programming
                 registered: [1993] Proceedings of the Twenty-sixth Hawaii International Conference on System Sciences | None | proceedings-article | authors: King; Srinivasan; Muggleton
      landing:   302 ieeexplore.ieee.org (http→https)  -> 落地页 BLOCKED at ieeexplore.ieee.org (network policy, proxy 403)
[9] doi:10.1038/s41598-026-54348-9
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · A temporal adaptive dictionary-constrained LDA and Bi-calibrated dual granularity DTM framework for dynamic topic evolut…
                 registered: Scientific Reports | 2026 | journal-article | authors: Yin
      landing:   302 www.nature.com  -> 落地页 BLOCKED at www.nature.com (network policy, proxy 403)
[10] doi:10.18559/ebr.2023.2.732
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · The rise of generative AI and possible effects on the economy
                 registered: Economics and Business Review | 2023 | journal-article | authors: Orchard; Tasiemski
      landing:   302 journals.ue.poznan.pl  -> 落地页 BLOCKED at journals.ue.poznan.pl (network policy, proxy 403)

summary crossref: 题目一致: 10
summary landing:  落地页 BLOCKED at dl.acm.org: 1 | 落地页 BLOCKED at ieeexplore.ieee.org: 1 | 落地页 BLOCKED at journals.ue.poznan.pl: 1 | 落地页 BLOCKED at linkinghub.elsevier.com: 2 | 落地页 BLOCKED at www.emerald.com: 1 | 落地页 BLOCKED at www.nature.com: 2 | 落地页 BLOCKED at www.science.org: 1 | 落地页 BLOCKED at www.tandfonline.com: 1
written: verified column in /home/user/novelty-probe-demo/evidence/evidence_table.md
```

---

## [2026-11-02 09:05 UTC] Step 63 — 用改进后的 verify.py 重新核验 v2 证据表

**命令**

```bash
python3 scripts/verify.py --table evidence/evidence_table_v2.md
```

**输出**（退出码 0）

```
verify run at 2026-11-02T09:05:44+00:00  table=evidence/evidence_table_v2.md
[1] doi:10.2139/ssrn.4389118
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · Artificial Intelligence and the Economics of Decision-Making
                 registered: - | 2023 | posted-content | authors: Naudé
      landing:   302 www.ssrn.com  -> 落地页 BLOCKED at www.ssrn.com (network policy, proxy 403)
[2] doi:10.1126/sciadv.adn5290
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the collective diversity of novel content
                 registered: Science Advances | 2024 | journal-article | authors: Doshi; Hauser
      landing:   302 www.science.org  -> 落地页 BLOCKED at www.science.org (network policy, proxy 403)
[3] doi:10.1038/s41586-025-09922-y
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · Artificial intelligence tools expand scientists’ impact but contract science’s focus
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
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · Issues of using artificial intelligence in scientific research of socio-economic processes
                 registered: Ufa Humanitarian Scientific Forum | 2025 | journal-article | authors: ?; Zulkarnay
      landing:   302 elibrary.ru  -> 落地页 BLOCKED at elibrary.ru (network policy, proxy 403)
[8] doi:10.1016/j.tics.2026.01.003
      crossref:  302 api.crossref.org  (attempts: 2)  -> Crossref HTTP 200 · 题目一致 · The homogenizing effect of large language models on human expression and thought
                 registered: Trends in Cognitive Sciences | 2026 | journal-article | authors: Sourati; S. Ziabari; Dehghani
      landing:   302 linkinghub.elsevier.com  -> 落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403)
[9] doi:10.48550/arxiv.2506.21818
      crossref:  302 data.crosscite.org  (attempts: 1)  -> Crossref BLOCKED at data.crosscite.org (network policy, proxy 403)
      openalex:  -> OpenAlex · 题目一致 · A systematic review of research on large language models for computer programming education
      landing:   302 arxiv.org  -> 落地页 BLOCKED at arxiv.org (network policy, proxy 403)
[10] doi:10.3390/cancers15092573
      crossref:  302 api.crossref.org  (attempts: 1)  -> Crossref HTTP 200 · 题目一致 · Artificial Intelligence in CT and MR Imaging for Oncological Applications
                 registered: Cancers | 2023 | journal-article | authors: Paudyal; Shah; Akin
      landing:   302 www.mdpi.com  -> 落地页 BLOCKED at www.mdpi.com (network policy, proxy 403)

summary crossref: OpenAlex 题目一致: 1 | 题目一致: 9
summary landing:  落地页 BLOCKED at arxiv.org: 1 | 落地页 BLOCKED at dl.acm.org: 1 | 落地页 BLOCKED at elibrary.ru: 1 | 落地页 BLOCKED at journals.sagepub.com: 1 | 落地页 BLOCKED at linkinghub.elsevier.com: 2 | 落地页 BLOCKED at www.mdpi.com: 1 | 落地页 BLOCKED at www.nature.com: 1 | 落地页 BLOCKED at www.science.org: 1 | 落地页 BLOCKED at www.ssrn.com: 1
written: verified column in evidence/evidence_table_v2.md
```

---

## [2026-11-02 09:07 UTC] Step 64 — 评估结论与文档更新

**评估结论**（Step 60、61 的 compare.py 输出；详见 `docs/IMPROVEMENT_PLAN.md` 第 12 节）

- 截断处并列：v1 42 → v1b 1；v2 32 → v2b 1。
- 噪声（Step 15 的定义）：v2 前 10 中 4 篇 → v2b 0 篇；v2b 前 20 中剩 1 篇（"narrow applications"）。
- 参考文献 Hao 等：v1、v1b 的检索结果中都没有；v1b 两步共被引（引用者按 scientists 过滤）排第 1；换用数据与方法面的词过滤时不在列表中（Step 57）。v2b 中 Nature 版与 arXiv 版合并（原 arXiv 版单列第 60 名），排第 3。
- 局限：NOT 短语与共被引的过滤方式都是在知道问题或目标之后确定的，评估只说明修正对已知问题有效，不是独立验证。

**命令 1：核实 README 中的一处说法（python3 内联脚本）**：`textmatch.porter_stem` 与 Snowball 官方测试数据（snowball-data 的 porter/voc.txt 与 output.txt，调研子任务下载）逐行比对。

```
lines: 42603 mismatches: 0 []
```

**命令 2：文档**

```
# docs/IMPROVEMENT_PLAN.md：新增第 12 节"评估结果"，各问题的状态更新
# HOWTO.md（中英双语）：T2 提示词允许 AND NOT（运算符大写）；T3 说明 S2 本地重排与 NOT 的转换、可选的 qa.py；
#   T4 说明版本识别、正式发表年份、RRF 排序与 --legacy；T5 新增补摘要（enrich.py）并允许标注时使用补到的摘要；
#   verify.py 的 OpenAlex 回退与 --no-landing；新增 T5b 引文追踪；第 8 节加入 compare.py；常见问题与目录速查补充
# HANDOFF.md：现状、数据流、数据格式（S2 的 local_rank、合并结果新字段、enrichment、chase 文件）、脚本速查、
#   设计决策、已知问题（改为本轮之后仍需注意的事项）、自检数（45）、下一步编号
# AGENTS.md：检索式可用 AND NOT（运算符大写）；chase、compare、enrichment 文件的约定；merge.py 默认方法；
#   证据表可用补到的摘要（注明来源）、年份取正式发表版本、"研究问题"面按研究者的标准；判断空间扩展到 NOT 与追踪
# README.md（英文）：流程、脚本说明、评估结果、局限、目录
# PROJECT.md：目录表补充 docs/ 与新脚本
# 两张证据表：verified 列的格式说明补充 OpenAlex 一段（Step 62–63 已用改进后的 verify.py 刷新）
```

**命令 3：离线自检与语法检查**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests
```

```
Ran 45 tests

OK
```

`python3 scripts/search.py --dry-run` → 6/6 queries valid。

**产出文件**

- `docs/IMPROVEMENT_PLAN.md`、`HOWTO.md`、`HANDOFF.md`、`AGENTS.md`、`README.md`、`PROJECT.md`、`evidence/evidence_table.md`、`evidence/evidence_table_v2.md`（修改）
- 本轮评估产出：`queries/queries_v2b.json`；`results/raw/*_v1b.json`、`*_v2b.json`（含 `chase_*`）；`results/merged/merged_v1b.json`、`merged_v2b.json`、`candidates_v1b.csv`、`candidates_v2b.csv`、`chase_*_v1b.csv`、`chase_*_v2b.csv`、`compare_v1_v1b.json`、`compare_v2_v2b.json`；`evidence/enrichment_v1b.json`、`enrichment_v2b.json`

**备注**：推送到分支 `claude/vigilant-faraday-odzwe4`，需研究者通过 PR 合并。下一步编号为 Step 65。

---

## [2026-11-02 09:38 UTC] Step 65 — Semantic Scholar 配置 key 后的限速处理

**研究者告知与要求（本轮）**：PR #4 已合并。研究者已在云环境中为 api.semanticscholar.org 完成配置，限额为"每秒 1 个请求，所有接口合计"。今后列出决策点时，都要附上助手的处置建议与简要原因。

**命令 1：确认 key 生效（curl 与 python3 内联脚本，只读）**

```
环境变量 S2_API_KEY 未设置；请求头中故意带一个错误的 x-api-key 仍返回 200 → 代理会用配置的 key 覆盖请求头
GET /datasets/v1/release/latest/dataset/abstracts（只有带有效 key 才能取得下载链接）→ HTTP 200，files listed: 30
（返回的下载链接未保存）
```

**命令 2：不同请求间隔下的 429 次数（python3 内联脚本，同一个只读请求各发 8 次）**

```
start-to-start interval 2.0s: [429, 200, 200, 429, 200, 429, 429, 200]  (429s: 4)
start-to-start interval 1.5s: [429, 429, 429, 200, 429, 200, 429, 200]  (429s: 5)
start-to-start interval 1.1s: [200, 429, 429, 200, 429, 200, 429, 429]  (429s: 5)
429 正文：{"message": "Too Many Requests. Please wait and try again or apply for a key for higher rate limits. …", "code": "429"}
```

即使间隔 2 秒，也有约一半请求返回 429，间隔再大也没有明显改善；像是这个 key 的额度同时被别处占用（原因无法从本环境确认）。

**命令 3：脚本修改**

```
# search.py：新增 throttle()，get_json() 对发往 api.semanticscholar.org 的每个请求（含翻页与每次重试）先节流，
#   相邻两个 S2 请求的间隔不少于 S2_MIN_INTERVAL = 1.1 秒；去掉原来零散的 S2_PAUSE。429 仍按 2、4、8… 秒退避重试
# tests/test_pipeline.py：新增节流测试（模拟时钟）
```

**命令 4：实时检查（写入临时目录）**：v2b 检索式的 Q2（3 页）、Q3（1 页）只查 S2：

```
Q2 semanticscholar total_hits 2160 saved 25；Q3 semanticscholar total_hits 111 saved 25；2/2 requests succeeded
S2 requests: 11 gaps (s): [2.48, 1.17, 2.31, 1.34, 2.32, 4.34, 8.31, 1.25, 2.2, 4.3] min gap: 1.17
（4 个页面请求成功，其余 7 次为 429 后的重试）
```

**命令 5：离线自检**：`python3 -W error::ResourceWarning -m unittest discover -s tests` → Ran 46 tests … OK。

**文档**：HOWTO（中英双语：准备一节与常见问题）、HANDOFF（API key 表、已知问题 8a、编号）、README（Requirements）说明 S2 的限额与节流。

**产出文件**：`scripts/search.py`、`tests/test_pipeline.py`、`HOWTO.md`、`HANDOFF.md`、`README.md`（修改）

---

## [2026-11-02 15:01 UTC] Step 66 — 工具层架构审视与迭代计划

**研究者要求（本轮）**：教程部分到此为止，不再迭代某轮结果；迭代承重层工具本身的准确性、稳定性、适配性。先理解需求，再以架构师视角审视、调研成熟项目、制定计划、最后实施。另：今后决策点都附处置建议与理由。

**命令 1：代码盘点（python3 / grep 内联，只读）**

```
10 scripts 2736 lines; 2 test files 1037 lines; ~95 top-level constants in 9 files; 19 path constants bound to ROOT
cross-imports: 12; HTTP implementations: 2 (search.get_json, verify.fetch), 11 call sites; no cache
Chinese literals in output/error/help code lines: search 29, snowball 13, compare 5, merge 4, logrun 4, verify 4
Python 3.9+ API: Path.is_relative_to (5 sites)
```

**命令 2：兼容性矩阵（uv 安装 3.9、3.10 到会话临时目录；系统自带 3.11–3.13）**

```
python3.9 / 3.10 / 3.11 / 3.12 / 3.13 (Linux): Ran 46 tests … OK（每个版本）
```

**命令 3：三个并行调研子任务**（成熟项目架构；HTTP 层与测试；适配性），报告存档于会话临时目录。主会话复核其关键结论：

```
OpenAlex: filter=title_and_abstract.search:("generative AI OR ChatGPT) AND science → HTTP 200, count 21344,
  oql: get works with (generative AI "OR" ChatGPT "AND" science)   ← 未配对引号被静默改写，运算符成了词
OpenAlex: meta.x_query 含结构化 oqo（get_rows, filter_rows）；/works/doi:<不存在> → 404 text/html
OpenAlex 响应头: X-Ratelimit-Limit 10000, X-Ratelimit-Remaining 6738, X-Ratelimit-Reset 32570, X-Ratelimit-Cost-Usd 0（单条查询免费）
Crossref /works/<doi>/agency：本次请求遇 429（子任务当日实测返回 agency.id = datacite / crossref）
snowball.seeds_from_evidence：中文表头 → 1 个种子；同一行换英文表头 → []（复现）
json.loads(带 BOM 的文件) → JSONDecodeError: Unexpected UTF-8 BOM（复现）
```

子任务还发现主会话给它的提示里凭记忆写的 PRISMA-S DOI 有误（…01542-5），正确为 doi:10.1186/s13643-020-01542-z（Crossref 核对）。记录在此，作为规则 2 的反例。

**产出文件**：`docs/ARCHITECTURE_REVIEW.md`（新增：现状、问题清单、成熟项目做法、目标架构、五个阶段的计划、决策点）。

**备注**：阶段 0、1 不涉及研究者决策，接着实施；阶段 2 起的决策点列在该文件第 6 节。

---

## [2026-11-02 15:09 UTC] Step 67 — 工具层迭代阶段 0：卫生类修复

按 `docs/ARCHITECTURE_REVIEW.md` 第 5 节的阶段 0 实施，不改变任何检索、合并、核验的结果。

**做了什么**

- 新增包 `novelty_probe/`（纯标准库）：`io.py`（读 JSON 容忍 BOM 与 ```json 围栏；写文本固定 \n 换行；原子写；控制台 UTF-8 守卫）、`paths.py`（find_root、rel 输出正斜杠）、`defaults.py`（面的 key 与中英文标签、证据表列名别名）。
- 各脚本接入：所有 JSON 读取改用 load_json_lenient；所有 JSON 输出改用原子写；main() 开头 configure_console()；rel() 统一到 paths.rel。snowball 识别证据表的面时接受中文或英文标签（修复英文表头零种子）。logrun 保持独立（不依赖包），日志里的命令按系统引用规则生成并附 argv 的 JSON，换行固定 \n。
- `.gitattributes`（text=auto eol=lf）；`.gitignore` 加 `.cache/`。
- 教程产出复制到 `examples/tutorial/`（idea、facets、queries、v1/v2 的 results 与 evidence），测试件改从那里读；读取项目目录实时数据的测试在文件不存在时跳过。HOWTO §1 相应改写（不必手工备份）。
- 新增 `tests/test_core.py`（BOM/围栏、LF 与原子写、写失败不破坏旧文件、rel、find_root、面标签别名、英文表头种子）。

**命令：自检与"清空示例后"的模拟**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests      # 3.13: Ran 56 tests … OK；3.9: OK
# 在会话临时目录复制仓库，按 HOWTO §1 删除 facets/queries/results/evidence 的示例文件并重置日志后：
python3 -m unittest discover -s tests                                # OK (skipped=2)
python3 scripts/search.py --dry-run                                  # 6/6 queries valid
```

**产出文件**：`novelty_probe/{__init__,io,paths,defaults}.py`、`tests/test_core.py`、`examples/tutorial/**`、`.gitattributes`（新增）；`scripts/*.py`、`tests/test_offline.py`、`tests/test_pipeline.py`、`HOWTO.md`、`.gitignore`（修改）

---

## [2026-11-02 15:29 UTC] Step 68 — 工具层迭代阶段 1：统一 HTTP 客户端、缓存与录制回放、响应校验

按 `docs/ARCHITECTURE_REVIEW.md` 第 5 节的阶段 1 实施。

**新增**（`novelty_probe/`，纯标准库）

- `http.py`：Client，四种模式 live / cache / record / replay；按主机限速（S2 1.1 秒，含重试与翻页）；读 Retry-After；退避 = 基数 × 2^(n+1)、封顶、等抖动；Retry-After > 60 秒或 OpenAlex "Insufficient budget" → 不重试；连续 429 熔断；跟随跳转时逐跳限速与重试，https → http 改用 https；错误分类（ClientError / NotFound / RateLimited / BudgetExhausted / ServerError / NetworkError / BlockedByPolicy / ContentError / ReplayMiss），非 JSON 错误体只取去标签后的摘要；密钥按主机加在请求头（OPENALEX_API_KEY → Bearer，S2_API_KEY → x-api-key），不落盘；OpenAlex 额度头与 Crossref 限速头进 stats；paginate()（cursor / token / offset）带断点续跑，令牌失效则从头再来。
- `cache.py`：内容寻址缓存与录制件同一条目格式；键 = sha256(method, 规范化 URL（去 api_key / mailto）, Accept, 请求体)；头部白名单；429 / 5xx 不缓存。
- `schemas.py`：OpenAlex 列表 / 记录、S2 bulk / batch / citations、Crossref works / agency、CSL JSON、本项目原始结果文件的形状校验（返回警告，不中断）。

**接入**：search（OpenAlex 校验 `x_query`：运算符被当成引号内的词 → 报错不保存；有排除组却无 NOT → 报错；oqo 解析树的词集合与发送的不同 → 警告；S2 用 paginate 翻页并写断点）、verify（先查 Crossref 的 /works/<doi>/agency：非 Crossref 登记的 DOI 直接记 "Crossref 无记录（DataCite 登记的 DOI）" 并走 OpenAlex，不再走 data.crosscite.org 那一跳）、snowball（翻页断点；ID 批量请求先排序再分批，保证请求确定）、enrich、authors；所有脚本新增 `--http-mode / --cache-dir / --cassette / --refresh`，输出 meta 带 `http` 统计与 `warnings`。

**命令：实时冒烟并录制（record 模式，写入会话临时目录）**

```
search --ids Q3,Q4（v1 检索式）：4/4 requests succeeded；OpenAlex Q3 warnings: []，credits_used 10，remaining 6728；
  S2 Q3：1 次 429 后重试成功（sleep 1.83 s），pool retrieved 9
verify 3 行（Science Advances / arXiv / Emerald）：Crossref 题目一致 ×2；arXiv DOI → agency=datacite → OpenAlex 题目一致；
  落地页三家均 BLOCKED（本环境网络策略）；Crossref 限速头 10/1s
snowball 一步（种子 doi:10.1145/3635636.3656204，--max-forward 30）：pool 79；共被引（scientist*）：185 篇引用者中 1 篇通过过滤
```

录制件（已去除密钥）存入 `tests/fixtures/cassettes/`（4 个，1.3 MB），回放测试在禁网状态下跑完 search / verify / snowball 的主流程并逐条校验录制响应的形状。

**命令：自检**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests   # 3.13: Ran 76 tests … OK；3.9: OK
```

新增 `tests/test_http.py`（假传输层：退避序列、Retry-After、预算、403/404 不重试、BlockedByPolicy、S2 间隔含重试、熔断、密钥只发给对应主机、跳转链与 https 升级、缓存命中与过期回退、录制 → 回放、键规范化、分页断点与令牌失效、形状校验）、`tests/test_replay.py`（录制件回放与契约）；`tests/test_core.py` 加 3.9 兼容性的静态检查（本轮即抓到 Path.write_text(newline=) 需 3.10+ 的问题）。

**产出文件**：`novelty_probe/{http,cache,schemas}.py`、`tests/{test_http,test_replay}.py`、`tests/fixtures/cassettes/*.json`、`tests/fixtures/verify_table_recorded.md`（新增）；`scripts/{search,verify,snowball,enrich,authors}.py`、`tests/{test_offline,test_pipeline,test_core}.py`、`HOWTO.md`、`HANDOFF.md`（修改）

---

## [2026-11-03 08:24 UTC] Step 69 — 工具层迭代阶段 2：配置文件、中英文界面、证据 JSON、CI 与网络护栏

**研究者的要求**：决策点全部按建议执行，继续阶段 2（研究者已在 GitHub 中开启 Actions）。六个决策：证据表以 JSON 为数据源并保留 Markdown 入口；Crossref 适配器实现但默认关闭（阶段 3）；单元测试禁网、另设 NP_LIVE=1 的联网检查（≤6 个请求）；GitHub Actions 矩阵 Python 3.9–3.13 × Ubuntu/Windows/macOS；阶段结束由助手开 PR 并订阅；退避带抖动（阶段 1 已实现）。

**2a 配置**：`novelty-probe.json`（项目根目录，只写与默认值不同的设置；仓库里的文件不改变任何参数，config_hash 与内置默认值相同）。`novelty_probe/config.py`：对象逐层合并、列表整体替换、`<键>_extend` 追加、`_` 开头为注释、未知键警告、取值不合法时一次列出所有问题；默认值的唯一定义处是 `novelty_probe/defaults.py`（面、取值、列名、版本识别前缀、停用词），`scripts/textmatch.py` 也从这里取。各脚本接入：search（各来源 top_n / enabled、S2 max_records、purpose 起始年份、截断词表）、merge 默认方法（top_k、rrf_k、BM25 k1/b、版本识别规则 `VersionRules`；`--legacy` 不读配置）、snowball（面、列名、停用词、默认参数）、verify（列名、落地页开关）、compare（标记词组 `--markers`）、enrich（年份窗口、top）。所有脚本新增 `--root / --config / --lang`；在另一个项目目录下运行时路径随之切换；logrun 用同样的规则找项目根目录并传给子进程。输出 meta 带 `config_file`、`config_hash`、所用参数。新增 `scripts/config.py`（show / show --diff / check / init）。检索式 id 的 `Q<数字>` 格式是脚本之间的文件名约定，不进配置；config_hash 不含 language 与 contact_email（不影响结果）。User-Agent 默认是通用的客户端名，contact_email 默认为空、助手不代填。

**2b 中英文界面**：`novelty_probe/i18n.py` 消息表；语言优先级 `--lang` > `NP_LANG` > 配置 language > zh，在构建参数解析器之前确定，帮助文本也随之切换。检索式语法错误、检索式文件问题、OpenAlex 解析核对、配置问题、HTTP 层错误、verify 的 verified 列都有中英文；中文文字与改造前逐字相同（已有测试与录制件依赖）。

**2c 证据 JSON**：`novelty_probe/evidence.py`（schema `novelty-probe/evidence@1`）与 `scripts/evidence.py`：
- `import-md`：表外文字原样保留；两张教程证据表导入后重新生成，与原文件逐字相同；
- `render`：可换语言（只有表头与有结构化结果的 verified 列变化）；Markdown 在上次导入或生成后被手工改过时不覆盖；
- `check`：取值合法、DOI / arXiv ID 来自检索结果、题目 / 年份 / 作者与检索结果一致、判定依据里引号内的英文是摘要（或检索记录题目）原文。本篇无摘要时，判定依据里注明 DOI、且在检索结果中的其他版本的摘要也算，对应 AGENTS.md 的规定。
verify 拆成结构化结果与展示文字（`novelty_probe/verification.py`）；`--table <json>` 时结构化结果写进 JSON，再重新生成 Markdown。snowball 的 `--from-evidence` 与证据 JSON 共用同一个解析器。

**2d CI 与测试**：`.github/workflows/tests.yml`（3.9–3.13 × 三个系统，离线测试 + 示例检索式 dry-run + 示例证据表检查）；`tests/netguard.py`：测试进程及其子进程中，除本机回环外的 DNS 与连接一律抛 NetworkBlocked（继承 BaseException，脚本的 except Exception 与 HTTP 重试都拦不住）；`tests/test_live_contract.py`：NP_LIVE=1 时的 6 项接口检查。

**回归核对**：把 v1b、v2b 的原始结果复制到临时项目目录，用 `merge.py --root <临时目录>` 重跑默认方法，合并记录与候选表和已提交的 `results/merged/merged_v1b.json`、`merged_v2b.json`、`candidates_v1b.csv`、`candidates_v2b.csv` 逐字节相同（meta 只多了 config_hash 与 parameters）；`--legacy` 的逐字节复现测试照常通过。

**命令：自检**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests   # 3.13: Ran 121 tests … OK (skipped=6)；3.9: 同
```

新增 `tests/test_config.py`（合并规则、校验、指纹、查找顺序、HTTP 策略覆盖、User-Agent、路径切换、语言探测、消息表完整性、配置到达各脚本、--root + --config 的合并端到端、英文命令行、config 命令）、`tests/test_evidence.py`（逐字还原、字段、英文生成、转义与原文单元格、直接写 JSON 的文档、检查的正反例、作者、注明来源的其他版本、引文比对、种子、命令行与手改保护、英文表全流程、verify 写回 JSON）；`tests/test_offline.py` 加英文 verified 列与结构化结果的测试、logrun 的项目目录测试；`tests/test_core.py` 加网络护栏测试。

**产出文件**：`novelty-probe.json`、`novelty_probe/{config,i18n,runtime,evidence,verification}.py`、`scripts/{config,evidence}.py`、`tests/{netguard,test_config,test_evidence,test_live_contract}.py`、`tests/childguard/sitecustomize.py`、`.github/workflows/tests.yml`（新增）；`novelty_probe/{defaults,http,io}.py`、`scripts/*.py`、`tests/{test_offline,test_core}.py`、`HOWTO.md`、`HANDOFF.md`、`AGENTS.md`、`README.md`、`docs/ARCHITECTURE_REVIEW.md`（修改）。后面三步用 logrun 记录检查结果。

---

## [2026-11-03 08:25 UTC] Step 70 — 证据表机器检查：v1 证据表（evidence.py check）

**命令**

```bash
python3 scripts/evidence.py check evidence/evidence_table.md
# argv: ["python3", "scripts/evidence.py", "check", "evidence/evidence_table.md"]
```

**输出**（退出码 0）

```
检索结果：results/merged/merged.json；补充摘要：evidence/enrichment_v1b.json, evidence/enrichment_v2b.json；作者：evidence/authors.json
检查通过：10 行，没有发现问题
```

---

## [2026-11-03 08:25 UTC] Step 71 — 证据表机器检查：v2 证据表（evidence.py check）

**命令**

```bash
python3 scripts/evidence.py check evidence/evidence_table_v2.md
# argv: ["python3", "scripts/evidence.py", "check", "evidence/evidence_table_v2.md"]
```

**输出**（退出码 0）

```
检索结果：results/merged/merged_v2.json；补充摘要：evidence/enrichment_v1b.json, evidence/enrichment_v2b.json；作者：evidence/authors_v2.json
检查通过：10 行，没有发现问题
```

---

## [2026-11-03 08:25 UTC] Step 72 — 联网接口检查（NP_LIVE=1，6 个请求）

**命令**

```bash
env NP_LIVE=1 python3 -m unittest tests.test_live_contract -v
# argv: ["env", "NP_LIVE=1", "python3", "-m", "unittest", "tests.test_live_contract", "-v"]
```

**输出**（退出码 0）

```
test_1_openalex_boolean_list (tests.test_live_contract.TestLiveContracts.test_1_openalex_boolean_list) ... ok
test_2_openalex_rejects_wildcards (tests.test_live_contract.TestLiveContracts.test_2_openalex_rejects_wildcards) ... ok
test_3_semantic_scholar_bulk (tests.test_live_contract.TestLiveContracts.test_3_semantic_scholar_bulk) ... ok
test_4_semantic_scholar_batch (tests.test_live_contract.TestLiveContracts.test_4_semantic_scholar_batch) ... ok
test_5_crossref_work (tests.test_live_contract.TestLiveContracts.test_5_crossref_work) ... ok
test_6_crossref_agency_for_arxiv_doi (tests.test_live_contract.TestLiveContracts.test_6_crossref_agency_for_arxiv_doi) ... ok

----------------------------------------------------------------------
Ran 6 tests in 7.150s

OK
```

---

## [2026-11-03 09:09 UTC] Step 73 — 工具层迭代：总体计划与进度表（阶段 3 开始前）

**研究者的要求**：三个决策点按建议执行（`contact_email` 留空；教程的两张证据表保持 Markdown；进入阶段 3）；正式开始阶段 3 之前，先给出一份整体的任务计划与推进进度表。

**做了什么**：新增 `docs/ROADMAP.md`，内容：
- 目标与边界、每个阶段的完成标准；
- 六个阶段的总览与状态（0–2 完成，3 进行中，4、5 未开始）；
- 问题清单 21 项的处理状态（已解决 14、部分解决 4、未解决 3）；
- 阶段 3 的任务分解（3.1–3.8，含依赖与验收）及阶段 3 的整体验收标准；
- 阶段 4、5 的任务概要；
- 决策记录、待决策事项（附建议与理由）、风险与对策、推进方式。
此后每完成一项任务，就更新该表的状态列并推送到工作分支。`docs/ARCHITECTURE_REVIEW.md` 第 9 节的状态表改为指向本表，只保留各阶段实现与计划的出入；HANDOFF、HOWTO、README 加上指向本表的链接。

**新的待决策事项**（不阻塞阶段 3）：CI 矩阵是否加入 Python 3.14。建议加入并保留 3.9，理由见 `docs/ROADMAP.md` 第 7 节。

**产出文件**：`docs/ROADMAP.md`（新增）；`docs/ARCHITECTURE_REVIEW.md`、`HANDOFF.md`、`HOWTO.md`、`README.md`（修改）

---

## [2026-11-03 09:12 UTC] Step 74 — 录制测试件：OpenAlex 含 NOT 的检索式（v2b Q2，1 个列表请求）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/recproj --queries /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/recproj/queries/queries_v2b.json --ids Q2 --sources openalex --suffix _rec --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/recproj/cache --http-mode record --cassette tests/fixtures/cassettes/search_not.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/recproj", "--queries", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/recproj/queries/queries_v2b.json", "--ids", "Q2", "--sources", "openalex", "--suffix", "_rec", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/recproj/cache", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/search_not.json"]
```

**输出**（退出码 0）

```
query purpose     source          total_hits saved no_id  file / note
Q2    component   openalex              2756    25     4  results/raw/openalex_Q2_rec.json

1/1 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 09:24 UTC] Step 75 — 录制测试件：Crossref 检索（v1 Q3、Q4，各取 40 条，2 个请求）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj --queries /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/queries/queries.json --ids Q3,Q4 --sources crossref --suffix _rec --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache --http-mode record --cassette tests/fixtures/cassettes/search_crossref.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj", "--queries", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/queries/queries.json", "--ids", "Q3,Q4", "--sources", "crossref", "--suffix", "_rec", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/search_crossref.json"]
```

**输出**（退出码 0）

```
请求估算（上限）：crossref 最多 2 个请求
query purpose     source          total_hits saved no_id  file / note
Q3    application crossref           9619402    20     0  results/raw/crossref_Q3_rec.json
Q4    application crossref           4091211     0     0  results/raw/crossref_Q4_rec.json

2/2 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 09:26 UTC] Step 76 — 录制测试件：Crossref 检索（v1 Q1，取 40 条；本地判断改为现有文字须满足整条检索式后，Q3、Q4 没有记录通过，补录能通过的样例）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj --queries /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/queries/queries.json --ids Q1 --sources crossref --suffix _rec --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache3 --http-mode record --cassette tests/fixtures/cassettes/search_crossref.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj", "--queries", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/queries/queries.json", "--ids", "Q1", "--sources", "crossref", "--suffix", "_rec", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache3", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/search_crossref.json"]
```

**输出**（退出码 0）

```
请求估算（上限）：crossref 最多 1 个请求
query purpose     source          total_hits saved no_id  file / note
Q1    component   crossref            185188     0     0  results/raw/crossref_Q1_rec.json

1/1 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 09:26 UTC] Step 77 — 录制测试件：Crossref 检索（v2b Q2，含 NOT，取 40 条）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj --queries /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/queries/queries_v2b.json --ids Q2 --sources crossref --suffix _rec --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache4 --http-mode record --cassette tests/fixtures/cassettes/search_crossref.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj", "--queries", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/queries/queries_v2b.json", "--ids", "Q2", "--sources", "crossref", "--suffix", "_rec", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache4", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/search_crossref.json"]
```

**输出**（退出码 0）

```
请求估算（上限）：crossref 最多 1 个请求
query purpose     source          total_hits saved no_id  file / note
Q2    component   crossref          10176818     0     0  results/raw/crossref_Q2_rec.json

1/1 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 09:27 UTC] Step 78 — 录制测试件：Crossref 检索（三条简单检索式，各取 40 条，3 个请求；用于回放测试中有记录通过的情形）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj --queries tests/fixtures/crossref_queries.json --sources crossref --suffix _rec --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache6 --http-mode record --cassette tests/fixtures/cassettes/search_crossref.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj", "--queries", "tests/fixtures/crossref_queries.json", "--sources", "crossref", "--suffix", "_rec", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/crproj/cache6", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/search_crossref.json"]
```

**输出**（退出码 0）

```
请求估算（上限）：crossref 最多 3 个请求
query purpose     source          total_hits saved no_id  file / note
Q1    component   crossref           3223601     1     0  results/raw/crossref_Q1_rec.json
Q2    component   crossref           2533662     6     0  results/raw/crossref_Q2_rec.json
Q3    component   crossref           7678221     1     0  results/raw/crossref_Q3_rec.json

3/3 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 09:32 UTC] Step 79 — 联网接口检查（NP_LIVE=1，6 个请求；第 5 项改为 Crossref 检索）

**命令**

```bash
env NP_LIVE=1 python3 -m unittest tests.test_live_contract -v
# argv: ["env", "NP_LIVE=1", "python3", "-m", "unittest", "tests.test_live_contract", "-v"]
```

**输出**（退出码 0）

```
test_1_openalex_boolean_list (tests.test_live_contract.TestLiveContracts.test_1_openalex_boolean_list) ... ok
test_2_openalex_rejects_wildcards (tests.test_live_contract.TestLiveContracts.test_2_openalex_rejects_wildcards) ... ok
test_3_semantic_scholar_bulk (tests.test_live_contract.TestLiveContracts.test_3_semantic_scholar_bulk) ... ok
test_4_semantic_scholar_batch (tests.test_live_contract.TestLiveContracts.test_4_semantic_scholar_batch) ... ok
test_5_crossref_search (tests.test_live_contract.TestLiveContracts.test_5_crossref_search) ... ok
test_6_crossref_agency_for_arxiv_doi (tests.test_live_contract.TestLiveContracts.test_6_crossref_agency_for_arxiv_doi) ... ok

----------------------------------------------------------------------
Ran 6 tests in 7.562s

OK
```

---

## [2026-11-03 09:35 UTC] Step 80 — 工具层迭代阶段 3：检索式语法树、数据源注册表、Crossref 适配器、请求估算

**研究者的要求**：三个决策点按建议执行，进入阶段 3（计划与进度见 `docs/ROADMAP.md`，Step 73）。

**做了什么**（任务编号见 ROADMAP 第 4 节）：
- 3.1 文本匹配移入 `novelty_probe/text.py`，`scripts/textmatch.py` 转发（两种导入方式得到同一组对象）。
- 3.2 `novelty_probe/query.py`：检索式解析为语法树（组、词：单词 / 短语 / 截断词）；错误码 Q101–Q117、Q201 带位置，dry-run 用 ^ 标出；规范写法；evaluate()。
- 3.3 `novelty_probe/sources/`：数据源协议（序列化、检索、记录转换、不支持的写法、请求估算）与注册表；OpenAlex、Semantic Scholar 从 `search.py` 迁出；`search.py` 只做编排，旧函数名保留为转发；merge / qa / compare 从注册表取文件名前缀；`sources.register()` 可登记新数据源。
- 3.4 OpenAlex 解析树逐组核对：分组不同即报错不保存；NOT (a OR b) 的两种表示等价；结构不认识时只警告。
- 3.5 Crossref 适配器（默认关闭）：包含组的词合成一串发送，cursor 翻页最多 1000 条，本地按整条检索式筛选，与 S2 相同的本地重排；有损之处写进 meta.lossy；题目与摘要去掉 JATS 标签。
- 3.6 请求估算：dry-run 与运行开头打印各来源的请求上限与 OpenAlex 额度上限；运行中剩余额度不够时预警；引文追踪在第一页返回总数后打印请求数，按 ID 批量取数前打印批数。

**两个发现**：
1. 旧解析器放行的四类写法会让各来源检索到不同的内容：未配对的引号（OpenAlex 把运算符当成词，S2 收到另一条检索式）；逗号（只对 OpenAlex 报错，S2 照常检索）；括号内缺 OR、组之间缺 AND（各来源与本地判断的含义不一致）。现在都报错（Q112、Q111、Q115、Q116）。仓库与示例里 72 个原始结果文件记录的检索式全部仍能解析。
2. Crossref 的检索面向参考文献匹配：教程的 v1 Q1、Q3、Q4 与 v2b Q2 各取前 40 条，本地满足检索式的都是 0 条（Step 75–77；常见词 generative AI、large language models 占满前列，多数记录没有摘要）。起初沿用 S2 对无摘要记录的宽松规则时，Q3 保存了 20 条只命中常见词的记录，于是改为现有文字须满足整条检索式。两三个词的简单检索式能找到相关记录（Step 78，如 Anderson 等 2024 的同质化研究，即 v1 证据表 rank 4）。

**回归核对**（以重构前的输出为基准，基准在重构前用同一脚本采集）：
- 28 条检索式（v1、v2、v2b 的示例与 10 条边界写法）的解析结果与 OpenAlex、S2 检索串逐字节相同（写成 `tests/fixtures/query_golden.json`）；
- 录制件回放的检索记录、引文追踪（一步与共被引）的记录与 CSV、核验后的表格逐字节相同；dry-run 每条检索式的输出相同，末尾多一行请求估算；
- `merge.py` 默认方法在另一个项目目录下重跑，v1b、v2b 的记录与候选表与已提交文件逐字节相同；`--legacy` 的逐字节复现测试照常通过。

**命令：自检**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests   # 3.13: Ran 141 tests … OK (skipped=6)；3.9: 同
```

新增 `tests/test_query_sources.py`（20 项）：基准对照、全部错误码与位置、英文报错、dry-run 的 ^ 位置、固定种子的 300 条随机检索式往返、OpenAlex 解析树的真实与改动样例、含 NOT 的录制件回放、Crossref 回放（保存的记录都满足检索式、教程长检索式保存 0 条、默认关闭）、请求估算与额度预警、临时登记的假数据源走通检索与合并、三个来源的合并。联网检查的第 5 项改为 Crossref 检索（Step 79，仍是 6 个请求）。

**产出文件**：`novelty_probe/{query,text}.py`、`novelty_probe/sources/{__init__,base,common,localrank,openalex,semanticscholar,crossref}.py`、`tests/test_query_sources.py`、`tests/fixtures/{query_golden,crossref_queries}.json`、`tests/fixtures/cassettes/{search_not,search_crossref}.json`（新增）；`scripts/{search,merge,snowball,textmatch}.py`、`novelty_probe/{config,i18n,schemas}.py`、`tests/{test_live_contract,test_replay}.py`、`HOWTO.md`、`HANDOFF.md`、`AGENTS.md`、`README.md`、`docs/ROADMAP.md`、`docs/ARCHITECTURE_REVIEW.md`（修改）

---

## [2026-11-03 13:55 UTC] Step 81 — 阶段 4 开始：研究者的决定与任务分解

**研究者的要求**（原话）："No need to add Python 3.14 to CI, keep Crossref off by default, I prefer RIS format. I agree to save authors with each search. There's no need adding duplicate-review table cause I'd like to reduce middle-stage human participations (damn, It's only a START of the whole research work!). I've merged and confirmed, you can start Phase 4 now."

**决定**：CI 不加 Python 3.14；Crossref 保持默认关闭；导出只做 RIS；检索时保存作者；不设去重复核表。由此定下的设计原则写入 `docs/ROADMAP.md` 第 1 节：**减少中间环节的人工参与**，脚本能自动完成、自动判断的就不留给研究者。

**做了什么**：更新 `docs/ROADMAP.md`：阶段 3 记为已合并（#6）；阶段 4 的任务分解按上述决定调整：
- 记录带作者与出处；
- 去重自动完成、规则编号可追溯，作者参与判断，不设复核表；
- 拆分合并脚本；
- 合并时自动写出 RIS、运行清单与检索报告；原计划的漂移检查并入运行清单；
- 量化本地匹配的偏差。
阶段 3 的任务表移到附录；待决策中新增阶段 5 的"一条命令跑完全部脚本步骤"（建议加）。

**产出文件**：`docs/ROADMAP.md`（修改）

---

## [2026-11-03 14:04 UTC] Step 82 — 重新录制测试件：S2 检索（v1 Q3、Q4；请求加 authors 字段）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4 --queries examples/tutorial/queries/queries.json --ids Q3,Q4 --sources semanticscholar --suffix _rec --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache --http-mode record --cassette /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/s2.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4", "--queries", "examples/tutorial/queries/queries.json", "--ids", "Q3,Q4", "--sources", "semanticscholar", "--suffix", "_rec", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache", "--http-mode", "record", "--cassette", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/s2.json"]
```

**输出**（退出码 0）

```
请求估算（上限）：semanticscholar 最多 6 个请求
query purpose     source          total_hits saved no_id  file / note
Q3    application semanticscholar          9     9     0  results/raw/semanticscholar_Q3_rec.json
Q4    application semanticscholar          1     1     0  results/raw/semanticscholar_Q4_rec.json

2/2 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 14:05 UTC] Step 83 — 重新录制测试件：Crossref 检索（v1 Q1、Q3、Q4，各取 40 条；请求加 author 字段）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4 --queries examples/tutorial/queries/queries.json --ids Q1,Q3,Q4 --sources crossref --suffix _rec --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache2 --http-mode record --cassette tests/fixtures/cassettes/search_crossref.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4", "--queries", "examples/tutorial/queries/queries.json", "--ids", "Q1,Q3,Q4", "--sources", "crossref", "--suffix", "_rec", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache2", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/search_crossref.json"]
```

**输出**（退出码 0）

```
请求估算（上限）：crossref 最多 3 个请求
query purpose     source          total_hits saved no_id  file / note
Q1    component   crossref            185379     0     0  results/raw/crossref_Q1_rec.json
Q3    application crossref           9620152     0     0  results/raw/crossref_Q3_rec.json
Q4    application crossref           4091899     0     0  results/raw/crossref_Q4_rec.json

3/3 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 14:05 UTC] Step 84 — 重新录制测试件：Crossref 检索（三条简单检索式，各取 40 条）

**命令**

```bash
python3 scripts/search.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4 --queries tests/fixtures/crossref_queries.json --sources crossref --suffix _rec2 --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache3 --http-mode record --cassette tests/fixtures/cassettes/search_crossref.json
# argv: ["python3", "scripts/search.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4", "--queries", "tests/fixtures/crossref_queries.json", "--sources", "crossref", "--suffix", "_rec2", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache3", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/search_crossref.json"]
```

**输出**（退出码 0）

```
请求估算（上限）：crossref 最多 3 个请求
query purpose     source          total_hits saved no_id  file / note
Q1    component   crossref           3224134     1     0  results/raw/crossref_Q1_rec2.json
Q2    component   crossref           2534477     6     0  results/raw/crossref_Q2_rec2.json
Q3    component   crossref           7678928     1     0  results/raw/crossref_Q3_rec2.json

3/3 个请求成功。total_hits = API 报告的命中数；saved = 保存的条数（前 25 条：OpenAlex 按 API 相关度，S2 在本地按相关度重排）；no_id = 既无 DOI 也无 arXiv ID 的条数（将标为 UNVERIFIED）。
```

---

## [2026-11-03 14:05 UTC] Step 85 — 重新录制测试件：引文追踪一步模式（种子 doi:10.1145/3635636.3656204；请求加 authorships）

**命令**

```bash
python3 scripts/snowball.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4 --seeds 10.1145/3635636.3656204 --queries examples/tutorial/queries/queries.json --suffix _rec --max-forward 30 --top 5 --keep 50 --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache4 --http-mode record --cassette tests/fixtures/cassettes/snowball_onehop.json
# argv: ["python3", "scripts/snowball.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4", "--seeds", "10.1145/3635636.3656204", "--queries", "examples/tutorial/queries/queries.json", "--suffix", "_rec", "--max-forward", "30", "--top", "5", "--keep", "50", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache4", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/snowball_onehop.json"]
```

**输出**（退出码 0）

```
seeds (1):
  10.1145/3635636.3656204: W4391556516 | refs 56 | cited by [191] | Homogenization Effects of Large Language Models on Human Creative Ideation
  OpenAlex 翻页：共 187 条，取 30 条，约 1 个请求（约 10 credits）
  按 ID 取 55 篇的元数据：2 个请求（约 20 credits）

pool: 85 works linked to the seeds (0 linked to more than one seed)
already in search results (none): 0
written: results/raw/chase_C1_rec.json, results/merged/chase_C1_rec.csv

path     rank  score    sim in_search  identifier                               title
onehop      1      1  0.242         -  doi:10.1145/3706598.3713146              Timing Matters: How Using LLMs at Different Timings Influences Writers
onehop      2      1  0.238         -  doi:10.1016/j.chbah.2025.100207          Homogenizing effect of large language models (LLMs) on creative divers
onehop      3      1  0.202         -  doi:10.1145/3715928.3737481              How AI Ideas Affect the Creativity, Diversity, and Evolution of Human 
onehop      4      1  0.193         -  doi:10.1177/00491241251327130            Generative AI Meets Open-Ended Survey Responses: Research Participant 
onehop      5      1  0.183         -  doi:10.1145/3290605.3300619              Mapping the Landscape of Creativity Support Tools in HCI
```

---

## [2026-11-03 14:05 UTC] Step 86 — 重新录制测试件：引文追踪共被引模式（同一种子，引用者过滤 scientist*）

**命令**

```bash
python3 scripts/snowball.py --root /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4 --seeds 10.1145/3635636.3656204 --queries examples/tutorial/queries/queries.json --suffix _rec --max-forward 30 --top 5 --keep 50 --cocite --citer-filter 'scientist*' --cache-dir /tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache5 --http-mode record --cassette tests/fixtures/cassettes/snowball_cocite.json
# argv: ["python3", "scripts/snowball.py", "--root", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4", "--seeds", "10.1145/3635636.3656204", "--queries", "examples/tutorial/queries/queries.json", "--suffix", "_rec", "--max-forward", "30", "--top", "5", "--keep", "50", "--cocite", "--citer-filter", "scientist*", "--cache-dir", "/tmp/claude-0/-home-user-novelty-probe-demo/942b2a24-db7a-5d82-970b-5376bbcb6aa8/scratchpad/rec4/cache5", "--http-mode", "record", "--cassette", "tests/fixtures/cassettes/snowball_cocite.json"]
```

**输出**（退出码 0）

```
seeds (1):
  10.1145/3635636.3656204: W4391556516 | refs 56 | cited by [191] | Homogenization Effects of Large Language Models on Human Creative Ideation
  OpenAlex 翻页：共 1 条，取 1 条，约 1 个请求（约 10 credits）
  按 ID 取 72 篇的元数据：2 个请求（约 20 credits）

citing works: 187 cite the seeds; 1 pass the filter 'scientists'; 0 letters/replies excluded; 1 citers used (versions of one work counted once: 0 merged)
co-cited: 72 works cited by the citers; 0 cited by at least 2
already in search results (none): 0
written: results/raw/chase_C2_rec.json, results/merged/chase_C2_rec.csv

path     rank  score    sim in_search  identifier                               title
citer       1         0.068         -  doi:10.1017/s0267190525000042            Digital accents, homogeneity-by-design, and the evolving social scienc
```

---

## [2026-11-03 14:32 UTC] Step 87 — 工具层迭代阶段 4：记录带作者、可追溯的自动去重、RIS、运行清单与检索报告

**研究者的要求**：按 Step 81 定下的范围实施阶段 4（减少中间环节的人工参与：作者随检索取得，不设去重复核表，RIS、运行清单与检索报告在合并时自动写出）。

**做了什么**（对应 `docs/ROADMAP.md` 第 4 节）：

- **4.1 记录带作者与出处**：
  - 检索记录增加 `authors`（最多 20 位）与 `n_authors`：OpenAlex 取自响应中原有的 authorships；S2 的请求加 `authors` 字段，Crossref 的 `select` 加 `author`，引文追踪加 `authorships`。
  - 合并记录增加 `authors`、`n_authors`、`field_source`（各字段取自哪条原始记录），schema 为 `novelty-probe/merged@2`；候选表加 `authors` 列（前 3 位，超过加 et al.）。
  - `authors.py` 先用合并记录里的作者，只为缺作者的候选查 OpenAlex；`evidence.py check` 用合并记录或 `authors*.json` 的作者比对，与任一处一致即可。
- **4.2 自动、可追溯的去重**：
  - 每个决定记规则编号（D1–D5 合并，R1–R8 保持分开），写进合并记录的 `dedupe_rules`、`review[].rule` 与 meta 的 `dedupe_rules`。
  - 作者作证据：同题但两边作者名没有一个相同时不并（R7）；题目几乎相同且有共同作者时才并（D5）；一方的作者名不可比（如只用汉字书写）时作者不作证据。
  - 合并组上限 `versions.max_cluster_groups = 6`（R8）。不设人工复核表。
- **4.3 拆分合并脚本**：记录组装、去重、排序移入 `novelty_probe/record.py`、`dedupe.py`、`rank.py`；`merge.py` 只做编排，`--legacy` 不变（只把重复的辅助函数改为从包内导入，并显式返回退出码 0）。
- **4.4 RIS**：合并时写出 `results/merged/candidates{后缀}.ris`；`scripts/export.py` 另可导出全部合并记录（`--all`）或证据表各行（`--evidence`，各面的标注写成关键词）。
- **4.5 运行清单与检索报告**：合并时写出 `run_manifest{后缀}.json`（`novelty-probe/manifest@1`）与 `search_report{后缀}.md`（参照 PRISMA-S，doi:10.1186/s13643-020-01542-z）；`scripts/report.py render` 换语言重新生成，`diff` 比较两次运行。各来源在报告里的说明由数据源适配器提供（`label`、`interface`、`ranking`）。
- **4.7 本地匹配的偏差（A4）**：`qa.py` 末尾与检索报告给出服务器已按布尔检索式返回、有摘要、却被本地判为不满足的比例。
- **4.8 测试**：新增 `tests/test_records.py`（13 项）；`test_evidence.py` 加合并记录作者的比对；联网接口检查加作者字段（S2 用检索时的字段）。

**编写测试时发现并修正的问题**：

1. 证据检查的作者比对只看排在最前的标识符：同时有 DOI 与 arXiv ID 的文献，作者与另一标识符下的记录一致也会误报。
2. 只用汉字等非拉丁字母书写的作者名没有可比的词，会被当成"没有共同的名字"而拆开同一篇（R7）。
3. `export.py` 导出候选时按默认方法的排序截取前 20 篇，对 `--legacy` 的结果与候选表不一致；改为按候选表的顺序。
4. `merge.py --legacy` 与 `authors.py` 没有显式返回退出码（实际退出码仍为 0）。

**命令与结果**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests            # Python 3.13.18：155 项通过（6 项联网检查跳过）
<Python 3.9.25> -W error::ResourceWarning -m unittest discover -s tests   # Python 3.9.25：155 项通过（6 项跳过）
NP_LIVE=1 python3 -m unittest tests.test_live_contract -v                  # 6 项通过（含 OpenAlex、S2、Crossref 的作者字段）
```

旧数据的回归核对（都没有作者）：

- **v1、v2（`examples/tutorial/`）**：默认方法的合并结果去掉新增字段（`authors`、`n_authors`、`field_source`、`dedupe_rules`，`review` 的 `rule`）与 bm25 后，与阶段 3 的代码（`git archive 0beca5e`）实际运行的结果相同；校验值 `a2b4ad3c1fdfc030`（v1）、`392d4b04ff1cbd0b`（v2）固定在 `tests/test_records.py`。
- **v1b、v2b**：在临时项目目录（`--root`）重新合并，记录除新增字段外与已提交的 `results/merged/merged_v1b.json`、`merged_v2b.json` 相同；候选表除 `authors` 列与 review 的规则编号外相同。
- **`--legacy`**：照常逐字节复现（测试）。

去重规则的使用次数（重新合并的结果）：

| 轮次 | 原始 → 合并 | 按标识符 | 按版本 | 保持分开 |
|---|---|---|---|---|
| v2 | 235 → 191 | D1 31、D2 5、D3 1 | D4 7 | R2 1、R3 1 |
| v1b | 216 → 164 | D1 41、D2 5 | D4 6 | R2 1、R3 1 |
| v2b | 234 → 190 | D1 30、D2 5、D3 2 | D4 7 | R2 1、R3 1、R6 1 |

v1、v2、v1b、v2b 中最大的合并组都是 2 个标识符分组（上限 6 未触发）。作者规则（D5、R7）在这些数据上不会触发（没有作者），由测试覆盖，下一轮真实检索时才会用上。

本地匹配的偏差（`qa.py`）：

| 轮次 | OpenAlex | Semantic Scholar |
|---|---|---|
| v1b | 87 条中 1 条（1.1%） | 94 条中 6 条（6.4%） |
| v2b | 103 条中 1 条（1.0%） | 83 条中 0 条 |
| v2 | 101 条中 0 条 | 69 条中 0 条 |

录制件回放的端到端流程（v1 Q3、Q4 → 合并）：13 篇全部带作者；`candidates.ris` 13 条、63 行作者；运行清单与检索报告齐全。

**未做的**：

- 用第三方 RIS 解析器（rispy）独立核对 RIS：运行下载的代码被环境的权限检查拦下，未运行；RIS 的结构由测试覆盖，建议研究者把一个 `candidates*.ris` 导入 Zotero 确认一次。
- 已提交的 v1、v2、v1b、v2b 合并结果没有重新生成，仍是阶段 3 的格式；重跑 `merge.py` 即得到新字段与 RIS、运行清单、检索报告。

**产出文件**：

- 新增：`novelty_probe/record.py`、`novelty_probe/dedupe.py`、`novelty_probe/rank.py`、`novelty_probe/export.py`、`novelty_probe/report.py`、`scripts/export.py`、`scripts/report.py`、`tests/test_records.py`
- 修改：`novelty_probe/sources/`（common、base、openalex、semanticscholar、crossref）、`novelty_probe/text.py`、`novelty_probe/evidence.py`、`novelty_probe/schemas.py`、`novelty_probe/config.py`、`novelty_probe/i18n.py`、`scripts/merge.py`、`scripts/authors.py`、`scripts/qa.py`、`scripts/snowball.py`、`tests/`（test_offline、test_replay、test_evidence、test_live_contract；录制件 search_q3q4、search_crossref、snowball_onehop、snowball_cocite）、`.gitattributes`
- 文档：`HOWTO.md`、`HANDOFF.md`、`AGENTS.md`、`README.md`、`docs/ROADMAP.md`、`docs/ARCHITECTURE_REVIEW.md`
