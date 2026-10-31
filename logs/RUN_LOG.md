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
