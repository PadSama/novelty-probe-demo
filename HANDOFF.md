# 交接文档：novelty-probe 本地移植

> **写给**：在本地用 ZCode + GLM 5.3 接手本项目的研究者本人，以及 ZCode 里的 AI 助手。
>
> **范围**：项目现状、本地环境准备、在 ZCode 里的用法、数据格式约定、脚本速查、已定的设计决策、已知问题、Git 与发布流程、检查清单。操作步骤见 `HOWTO.md`，AI 助手的行为规则见 `AGENTS.md` 与 `PROJECT.md`。

## 1. 项目是什么

一个围绕研究想法检索文献证据的流程：

1. 把想法拆成五个面（研究问题、作用机制、研究情境、数据与方法、预期发现）；
2. 组合布尔检索式，检索 OpenAlex 和 Semantic Scholar；
3. 合并去重（识别预印本与正式版），按相关度排序，对前 10 篇候选逐面标注 overlap / differ / unknown；
4. 用 Crossref（查不到时用 OpenAlex）核验每个 DOI；
5. 可选：从证据表中的相关文献出发做引文追踪，补关键词检索因措辞不同而漏掉的文献。

流程**不判断新颖性**，只整理可核验的证据，由研究者判断。

## 2. 当前状态

| 项目 | 状态 |
|---|---|
| 仓库 | https://github.com/PadSama/novelty-probe-demo （公开，MIT 许可证） |
| 发布 | v1.0.0（标签打在 3f00b7a） |
| v1.0.0 之后的改动 | CITATION.cff 加入 ORCID、标题大小写修正；交接文档 `AGENTS.md`、`HANDOFF.md`、`tests/`（Step 23）；针对第 9 节遗留问题的改进（Step 24–64，见 `docs/IMPROVEMENT_PLAN.md`）：NOT、S2 本地重排、版本识别与 RRF 排序、补摘要、引文追踪、核验回退、质量检查与结果比较脚本；工具层迭代（Step 66–72，见 `docs/ARCHITECTURE_REVIEW.md`）：共用包 `novelty_probe/`（HTTP 客户端、缓存与录制回放、配置 `novelty-probe.json`、中英文界面、证据 JSON 与检查）、离线测试的网络护栏、联网接口检查、GitHub Actions |
| 默认分支 | `main`，受规则集保护：禁止删除、禁止强推、必须通过 PR 合并（审批人数 0） |
| 引用信息 | `CITATION.cff`：作者 Yuan, Quan；ORCID 0009-0009-3011-3739；version 1.0.0 |
| 示例运行 | v1（未限定学科）与 v2（管理学与经济学）两轮的全部产出都在仓库里（用旧方法生成，`merge.py --legacy` 可逐字节复现）；v1b、v2b 是用改进后的流程重跑的评估轮（检索、合并、补摘要、引文追踪与比较，没有证据表）；全过程见 `logs/RUN_LOG.md` Step 0–65 |

## 3. 本地环境准备

### 3.1 获取代码

```bash
git clone https://github.com/PadSama/novelty-probe-demo.git
```

```bash
cd novelty-probe-demo
```

也可以解压 `novelty-probe.zip`，但压缩包里没有 git 历史，之后无法直接提交 PR。

### 3.2 Python

Python 3.9 或更高，只用标准库，不需要 `pip install` 任何东西。

```bash
python3 --version
```

Windows 上用 `python` 或 `py -3`，并建议设置环境变量 `PYTHONUTF8=1`，避免中文输出的编码问题。

### 3.3 API key

在云端环境里，OpenAlex 的 key 是由 Network secrets 自动注入的。**本地没有这个机制，必须自己设置环境变量。**

| 变量 | 是否必需 | 说明 |
|---|---|---|
| `OPENALEX_API_KEY` | 实际上必需 | 免费申请：https://help.openalex.org/api/authentication/ 。没有 key 时共用每日额度，很容易遇到 429 |
| `S2_API_KEY` | 可选 | https://www.semanticscholar.org/product/api#api-key-form 。有 key 时的限额是**每秒 1 个请求，所有接口合计**；`search.py` 对发往 S2 的每个请求（含翻页与重试）统一节流（间隔 ≥ `S2_MIN_INTERVAL` = 1.1 秒），不要同时运行两个访问 S2 的脚本。云环境中研究者已在网络设置里为 api.semanticscholar.org 配置 key（2026-11-02，由代理注入） |

macOS / Linux（只对当前终端有效；写进 `~/.zshrc` 或 `~/.bashrc` 可长期有效）：

```bash
export OPENALEX_API_KEY="你的 key"
```

Windows PowerShell（当前窗口有效）：

```powershell
$env:OPENALEX_API_KEY = "你的 key"
```

Windows 长期有效（新开的窗口才生效）：

```powershell
setx OPENALEX_API_KEY "你的 key"
```

### 3.4 网络

- **需要访问的域名**：在自己电脑上通常不用设置。需要能访问 `api.openalex.org`、`api.semanticscholar.org`、`doi.org`、`api.crossref.org`；`data.crosscite.org` 和出版商网站可选（arXiv 等 DataCite DOI 在 Crossref 查不到时，`verify.py` 会改查 OpenAlex）。
- **需要代理的网络**：设置 `HTTPS_PROXY`。脚本用 Python 标准库 `urllib`，会自动读取这个变量。
- **macOS 证书问题**：用 python.org 安装包装的 Python，可能报 `CERTIFICATE_VERIFY_FAILED`。运行 `/Applications/Python 3.x/Install Certificates.command` 即可。

### 3.5 离线自检（必做）

```bash
python3 -m unittest discover -s tests -v
```

应显示 `OK (skipped=6)`，用时十秒左右，不联网，也不改动仓库文件（6 项跳过的是联网接口检查，见 3.6）。测试件读 `examples/tutorial/` 下的教程产出副本，其中一项按旧方法（`merge.py --legacy`）重跑合并，再和已提交的 v1、v2 合并结果逐字节比较；回放测试用 `tests/fixtures/cassettes/` 里录制的真实响应跑完 search / verify / snowball 的主流程。全部通过，说明本机的 Python 和脚本逻辑与原环境一致。

测试里装有网络护栏（`tests/netguard.py`）：除本机回环地址外，任何 DNS 查询或连接都会直接报错，子进程同样如此。GitHub Actions（`.github/workflows/tests.yml`）在 Python 3.9–3.13 × Ubuntu / Windows / macOS 上跑同一套离线测试。

### 3.6 联网冒烟测试（可选，只发 2 个检索请求，不覆盖示例产出）

```bash
python3 scripts/search.py --dry-run
```

```bash
python3 scripts/search.py --ids Q1 --suffix _smoke
```

```bash
python3 scripts/merge.py --suffix _smoke
```

确认生成了 `results/raw/openalex_Q1_smoke.json`、`results/raw/semanticscholar_Q1_smoke.json`、`results/merged/merged_smoke.json`、`results/merged/candidates_smoke.csv`，然后删除这些测试文件：

```bash
rm -f results/raw/*_smoke.json results/merged/*_smoke.*
```

冒烟测试只是检查环境，不属于研究步骤，可以不写进 RUN_LOG。

**联网接口检查**（6 个请求，约 10 秒）：确认 OpenAlex、Semantic Scholar、Crossref 的接口行为仍与脚本的假设一致（OpenAlex 的布尔解析与响应形状、不支持通配符；S2 bulk 与 batch；Crossref works 与 agency）。建议每轮 T3 之前跑一次：

```bash
NP_LIVE=1 python3 -m unittest tests.test_live_contract -v
```

## 4. 在 ZCode 里使用 GLM 5.3

1. 在 ZCode 中打开项目根目录。如果 ZCode 会自动读取项目里的规则文件，确认它读到了 `AGENTS.md`；如果不会，就用下面的第一条消息让它去读。
2. 第一条消息建议这样写，先确认它理解了规则再开工：

   ```text
   请先阅读本项目的 AGENTS.md、PROJECT.md、HOWTO.md、HANDOFF.md，然后：
   1) 复述 PROJECT.md 的三条硬规则；
   2) 说明 T1–T6 每一步由谁完成、产出什么文件；
   3) 运行 python3 -m unittest discover -s tests -v，并报告结果。
   在我确认之前，不要修改任何文件。
   ```

3. 需要助手完成的步骤是：T2（拆面与检索式）、T5（证据表标注）、T6 第 1 节（选出最接近的三篇）。提示词在 `HOWTO.md` 第 3、6、7 节，中英文任选。T5b 引文追踪的种子和过滤词组由你决定，助手只运行脚本、整理结果。
4. 脚本步骤可以让助手执行，也可以自己在终端执行，命令一律用 `logrun.py` 包起来。
5. 每一步结束后检查三件事：命令和产出是否写进了 RUN_LOG；DOI、作者是否都来自检索结果；有没有出现新颖性结论。

**换用 GLM 后要特别留意的地方**（都来自本项目实际遇到过的问题，前三条已由 `search.py` 自动检查，第四条由 `verify.py` 检查）：

- 助手可能把 JSON 包在 Markdown 代码块里写进 `queries.json`，`search.py` 会报"不是合法的 JSON"；
- `id` 必须是 Q1–Q6 这样的格式，`purpose` 必须是四个取值之一；
- 检索式里不能有未登记的截断符 `*` 和逗号；运算符必须大写，排除只能写成 `AND NOT (…)` 放在最后（小写 not 在 OpenAlex 里会把排除变成包含，`search.py` 会拦截）；
- 证据表的列名必须完全一致（`DOI/arXiv`、`verified`），否则 `verify.py` 找不到列；
- 判定依据的引文必须逐字来自摘要；作者用 `scripts/authors.py` 查，不能凭记忆写。

## 5. 结构与数据流

```text
idea/idea.md
  │  T2 AI 助手
  ▼
facets/facets.md + queries/queries.json
  │  T3 scripts/search.py ──► OpenAlex（title_and_abstract.search）、Semantic Scholar（bulk）
  ▼
results/raw/{来源}_{Qn}{后缀}.json        每条检索式 × 每个来源，前 25 条（S2 取回全部命中后本地重排）
  │  （可选）scripts/qa.py：标题 + 摘要满足检索式的比例
  │  T4 scripts/merge.py：DOI / arXiv ID 去重 → 版本识别 → RRF 排序
  ▼
results/merged/merged{后缀}.json + candidates{后缀}.csv（前 20 篇）
  │  T5 scripts/authors.py ──► OpenAlex /works/doi:
  │  T5 scripts/enrich.py ──► OpenAlex title.search（同一研究的其他版本）
  ▼
evidence/authors.json + enrichment.json ──► AI 助手标注 ──► evidence/evidence_table.md（可选导入为 .json）
  │  T5 scripts/evidence.py check：取值、标识符来自检索结果、题目 / 年份 / 作者、引文是摘要原文
  │  T5 scripts/verify.py ──► doi.org → Crossref 元数据（失败时 OpenAlex）；doi.org → 出版商落地页
  ▼
verified 列写回证据表
  │  T5b（可选）scripts/snowball.py ──► OpenAlex referenced_works / cites:
  ▼
results/raw/chase_{标签}{后缀}.json + results/merged/chase_{标签}{后缀}.csv ──► 研究者挑选后补入证据表
  │  T6 AI 助手 + 研究者
  ▼
evidence/difference_statement.md
```

| 路径 | 作用 | 由谁生成 | 被谁读取 |
|---|---|---|---|
| `idea/idea.md` | 研究想法原文 | 研究者 | T2 |
| `facets/facets.md` | 五个面与检索词 | AI 助手（T2） | 研究者、T5 标注 |
| `queries/queries.json` | 6 条布尔检索式 | AI 助手（T2） | `search.py` |
| `results/raw/{来源}_Q*.json` | 原始检索结果 | `search.py` | `merge.py`、`qa.py` |
| `results/merged/merged*.json` | 去重后的全部文献 | `merge.py` | 研究者、AI 助手、`snowball.py`、`compare.py` |
| `results/merged/candidates*.csv` | 前 20 篇候选 | `merge.py` | `authors.py`、`enrich.py`、T5 标注 |
| `evidence/authors*.json` | 候选的作者 | `authors.py` | T5 标注 |
| `evidence/enrichment*.json` | 从其他版本补到的摘要、arXiv ID（带来源） | `enrich.py` | T5 标注 |
| `results/raw/chase_*.json`、`results/merged/chase_*.csv` | 引文追踪结果 | `snowball.py` | 研究者、`compare.py` |
| `results/merged/compare_*.json` | 几轮结果的比较 | `compare.py` | 研究者 |
| `docs/IMPROVEMENT_PLAN.md` | 遗留问题的调研、计划与评估 | AI 助手 | 研究者 |
| `evidence/evidence_table*.md` | 逐面标注与 DOI 核验 | AI 助手 + `verify.py` | 研究者、T6 |
| `evidence/difference_statement.md` | 差异陈述 | AI 助手（第 1 节）+ 研究者（第 2、3 节） | 研究者 |
| `logs/RUN_LOG.md` | 只追加的运行日志 | `logrun.py` + AI 助手 | 所有人 |
| `novelty-probe.json` | 项目配置（只写与默认值不同的设置） | 研究者（`scripts/config.py init` 生成最小文件） | 所有脚本 |
| `evidence/evidence_table*.json` | 证据表的 JSON 形式（可选；以它为数据源时 Markdown 由它生成） | `evidence.py import-md`、`verify.py --table *.json` | `evidence.py`、`verify.py`、`snowball.py` |
| `novelty_probe/` | 共用包：`http.py`（客户端）、`cache.py`、`schemas.py`（响应形状校验）、`config.py`、`i18n.py`、`runtime.py`（通用参数）、`evidence.py`、`verification.py`、`defaults.py`、`io.py`、`paths.py` | — | 所有脚本 |
| `tests/` | 离线自检：`test_offline`、`test_pipeline`、`test_core`、`test_http`、`test_replay`、`test_config`、`test_evidence`；`test_live_contract`（NP_LIVE=1 才运行）；`tests/fixtures/` 为词干还原对照表与录制件 | — | 改代码后运行 |

## 6. 数据格式约定

### 6.1 `queries/queries.json`

JSON 数组，每条形如：

```json
{"id": "Q1", "facets_used": ["mechanism", "context"], "query": "(\"large language models\" OR \"generative AI\") AND (homogenization OR \"collective diversity\")", "purpose": "component"}
```

- **语法**：用 AND 连接若干个括号组，括号内只用 OR；短语加英文双引号；运算符一律大写；不用嵌套括号和逗号。排除写成 `AND NOT ("a" OR "b")`，放在包含组之后：OpenAlex 原样发送（脚本检查 `x_query.oql` 中确有 NOT，否则报错不保存），S2 译为 `+ -(…)`。小写的 and / or / not 和以 `-`、`!` 开头的词会被拒绝（OpenAlex 把小写 not 当普通词，实测会把排除变成必须包含）。
- **检查**：`search.py` 的 `load_queries()` 检查 JSON 格式、id 格式与是否重复、query 是否为空、purpose 取值；`--dry-run` 另外检查检索式语法，并打印两个来源实际会发送的检索串。
- **截断词**：只有 `search.py` 中 `TRUNCATION` 表登记过的截断词才能用（如 `bibliometric*`），其他截断词会报错。HOWTO 的提示词要求不用截断，这样最省事。

### 6.2 `results/raw/{source}_{id}{suffix}.json`

```text
{"meta": {...}, "records": [...]}
meta    source_api, query_id, purpose, queries_file, query_original, year_from, conversion, query_sent,
        api_interpretation（仅 OpenAlex）, request_url, sort, total_hits, returned, retrieved_at
records title, year, doi, arxiv_id, venue, abstract, source_api, query_id
        S2 记录另有 local_rank：groups_matched, bm25, has_abstract, citations（及 same_title_dropped）
```

DOI 已去掉 `https://doi.org/` 前缀，arXiv ID 已去掉版本号，OpenAlex 的摘要已由倒排索引还原成文本。S2 的 meta 另有 `retrieval_sort` 与 `pool`（取回条数、页数、是否截断、有摘要的条数、去掉的同题记录数）。旧结果（v1、v2）没有这些字段。

### 6.3 `results/merged/merged{suffix}.json`

```text
meta     created_at, script, dedup_rules, inputs, counts, candidates
records  merged_id, title, year, doi, arxiv_id, venue, abstract, id_status, alt_ids, title_linked,
         sources, query_ids, n_queries, n_sources, hits, mean_rank, raw_refs
```

- `id_status`：取值为 `DOI` / `arXiv` / `UNVERIFIED`。
- `raw_refs`：形如 `openalex_Q1#8`，即文件名去掉 `.json`，`#` 后是该条在文件中的名次。
- `merged_id`：编号规则固定，输入不变时编号也不变。
- 默认方法另有：`year_first`（最早版本的年份；`year` 为正式发表版本的年份）、`review`（[{with, reason}]，待人工核对的疑似同一研究）、`rrf`、`bm25`、`n_conform`（本地判断满足几条检索式）；meta 另有 `method`、`year`、`version_links`、`review_pairs`、`bm25_terms`、`ignored_phrases`。`--legacy` 的输出与旧格式完全相同。

### 6.4 `results/merged/candidates{suffix}.csv`

默认方法共 22 列：`rank, merged_id, rrf, bm25, n_conform, hits, n_queries, n_sources, mean_rank, query_ids, sources, id_status, doi, arxiv_id, title, year, year_first, venue, title_linked, review, raw_refs, abstract`；`--legacy` 为原来的 17 列（无 `rrf, bm25, n_conform, year_first, review`）。编码为带 BOM 的 UTF-8，Excel 可以直接打开。读取方（`authors.py`、`enrich.py`）按列名取值，两种格式都能用。

### 6.5 `evidence/authors{suffix}.json`

```text
meta     source, script, input, top, retrieved_at
records  rank, merged_id, doi, openalex_id, openalex_title, title_matches, authors, n_authors, error
```

### 6.5a `evidence/enrichment{suffix}.json`

```text
meta     source, script, input, top, max_year_gap, retrieved_at, counts
records  rank, merged_id, title, needs, versions[], abstract, abstract_source, arxiv_id_from_version, doi_from_version, error
```

`versions` 是在 OpenAlex 中按题目找到的同一研究的其他版本（标题相同、年份差 ≤3、至少一位作者同姓）；`abstract_source` 记补到的摘要来自哪条记录（OpenAlex ID、DOI、类型、年份、作者核对结果）。`doi_from_version` 只是线索，使用前要用 `verify.py` 核验。

### 6.5b `results/raw/chase_{label}{suffix}.json` 与 `results/merged/chase_{label}{suffix}.csv`

- 原始文件：记录格式同 6.2，另有 `chase`（path：onehop / cocited / citer；links 或 support；seeds、via、versions；similarity、query_blocks、conform）；只存排序后的前 `--keep` 条（默认 200），总数在 `meta.total_hits`。meta 记种子、过滤词组、引用者数、被排除的来信等。
- CSV：每条路径各取前 `--top` 条（默认 20），`in_search` 列为已在检索结果中的 merged_id。
- 文件名以 `chase_` 开头，`merge.py` 不读取，不进入检索结果的排序。

### 6.0 `novelty-probe.json`（项目配置）

- 只写与内置默认值不同的设置；`python3 scripts/config.py show` 打印有效配置，`show --diff` 只打印改动，`check` 检查写法。
- 合并规则：对象逐层合并；列表整体替换；`<键>_extend` 在默认列表后追加；以 `_` 开头的键是注释；未知的键给出警告。
- 默认值的唯一定义处是 `novelty_probe/defaults.py` 与 `novelty_probe/config.py` 的 `DEFAULTS`。
- 配置里放参数与词表（面、标注取值、列名别名、purpose 与起始年份、截断词表、各来源的条数、RRF / BM25 参数、版本识别的前缀与年份窗口、停用词、引文追踪与比较的默认值、按主机的 HTTP 策略），不放方法本身（词干还原、BM25 与 RRF 的公式、版本识别规则的顺序、检索式 id 的 `Q<数字>` 格式、AND NOT 必须大写）。
- `config_hash`：有效配置（去掉 `contact_email` 与 `language`）的 sha256 前 12 位，写进每个输出文件的 meta。
- `contact_email` 默认为空。填写后加进 User-Agent（Crossref 的礼貌池）；不填时 User-Agent 只是通用的客户端名。

### 6.6 `evidence/evidence_table{suffix}.md`

- 表头必须有 `DOI/arXiv`、`verified`；`rank` 和 `题目`（或 `Title`）用于题目比对。
- 五个面的取值只能是 `overlap` / `differ` / `unknown`。
- verified 列格式为"Crossref 结果；落地页结果"，由 `verify.py` 写入；Crossref 失败时中间多一段 OpenAlex 的结果。
  - "Crossref HTTP 200 · 题目一致 · …"：DOI 有效，且指向表中这篇；
  - "OpenAlex · 题目一致 · …"：Crossref 查不到（如 arXiv 等 DataCite DOI），OpenAlex 按 DOI 查到且题目一致；
  - "BLOCKED at <域名>"：该域名不允许访问；
  - "落地页 skipped"：用了 `--no-landing`；
  - "UNVERIFIED"：没有 DOI。
- "研究问题"面的 overlap 条件已按研究者的标准修订（去掉研究情境后问题相同：个人使用 AI，集体是否趋同），见两张表末尾的修订记录与 Step 25。
- 判定依据每篇以 `**rank · merged_id**` 开头（`evidence.py` 据此把依据与表格行对应）。
- `python3 scripts/evidence.py check <表>` 机器检查：取值、标识符来自检索结果、题目 / 年份 / 作者与检索结果一致、引号内英文为摘要（或检索记录题目）原文；本篇无摘要时，判定依据中注明 DOI 的其他版本（在检索结果中）的摘要也算。两张教程证据表全部通过（Step 70–71）。
- JSON 形式（`evidence/evidence_table{suffix}.json`，schema `novelty-probe/evidence@1`）：`meta`（语言、面、取值、列、检索结果文件、对应的 Markdown、上次生成的 sha256）、`sections`（表外文字，原样保留）、`rows`（rank、merged_id、作者、年份、题目、doi、arxiv_id、各面取值、`verification` 结构化核验结果或 `verified_text`、判定依据）。从 Markdown 导入后再生成，与原文件逐字相同；换语言生成时只有表头与 verified 列（有结构化结果时）变化。教程的两张表仍以 Markdown 为准，没有提交 JSON。

### 6.7 `logs/RUN_LOG.md`

- **只追加**：新条目一律写在末尾，不改写已有条目。
- **条目格式**：以 `---` 分隔，标题写成 `## [YYYY-MM-DD HH:MM UTC] Step N — 标题`，正文包含研究者的要求、命令、输出、产出文件、备注。
- **编号**：下一步是 **Step 73**。
- **旧哈希**：Step 20 之前的条目里引用的是改写历史之前的提交哈希，按 Step 20 的对照表查新哈希。

## 7. 脚本速查

| 脚本 | 作用 | 常用参数 | 访问网络 | 退出码 |
|---|---|---|---|---|
| `search.py` | T3 检索 | `--dry-run`、`--ids`、`--sources`、`--queries`、`--suffix` | api.openalex.org、api.semanticscholar.org | 0 全部成功；1 有请求失败，或 dry-run 发现语法错误；2 检索式文件不合格或参数错误 |
| `qa.py` | 检索质量检查（可选） | `--suffix` | 无 | 0 |
| `merge.py` | T4 合并去重、版本识别、RRF 排序、前 20 候选 | `--suffix`、`--legacy` | 无 | 0 成功；没有记录或同一来源混有不同检索方式时报错退出 |
| `authors.py` | T5 查作者 | `--top`、`--candidates`、`--out` | api.openalex.org | 0（单条失败记在 `error` 字段里） |
| `enrich.py` | T5 从其他版本补摘要 | `--top`、`--candidates`、`--out` | api.openalex.org | 0（单条失败记在 `error` 字段里） |
| `verify.py` | T5 DOI 核验 | `--table`、`--no-landing` | doi.org、api.crossref.org、api.openalex.org、出版商网站 | 0 元数据核验（Crossref 或 OpenAlex）全部成功；1 有失败 |
| `snowball.py` | T5b 引文追踪（一步 / 两步共被引） | `--from-evidence` 或 `--seeds`、`--cocite`、`--citer-filter`、`--min-support`、`--label`、`--suffix` | api.openalex.org | 0 |
| `compare.py` | 比较几轮结果、已知文献名次 | `--runs`、`--known`、`--ignore-phrases`、`--out` | 无 | 0 |
| `evidence.py` | 证据表：检查、Markdown 转 JSON、JSON 生成 Markdown | `check`、`import-md`、`render`；`--results`、`--authors`、`--enrichment`、`--out`、`--force` | 无 | check：0 没有问题，1 有问题；2 文件无法读取 |
| `config.py` | 查看与检查配置 | `show`、`show --diff`、`check`、`init` | 无 | 0；配置有误时 2；`init` 遇到已有文件时 1 |
| `logrun.py` | 运行命令并写日志 | `[--root 目录] "<步骤名>" -- <命令>` | 无 | 与被运行的命令相同；用法错误时为 1 |

所有脚本都接受 `--root`（项目根目录；默认从当前目录向上找 `novelty-probe.json` 或 `PROJECT.md`，或环境变量 `NOVELTY_PROBE_ROOT`）、`--config`（或 `NOVELTY_PROBE_CONFIG`）、`--lang zh|en`（或 `NP_LANG`，或配置 `language`）。配置有误时以退出码 2 结束，并一次列出所有问题。`logrun.py` 用同样的规则确定项目根目录，并通过 `NOVELTY_PROBE_ROOT` 传给子进程。

所有联网脚本（search、authors、enrich、verify、snowball）共用 `novelty_probe/http.py` 的客户端，并接受同一组参数：`--http-mode live|cache|record|replay`（或环境变量 `NP_HTTP_MODE`）、`--cache-dir`（默认 `.cache/http`，已 gitignore）、`--cassette`（录制件路径）、`--refresh`。每个输出文件的 `meta.http` 记录请求数、缓存命中、重试、OpenAlex 额度头；`meta.warnings` 记录响应形状与解析核对的警告。S2 翻页与引文追踪的断点写在 `results/raw/.checkpoints/`，中断后重跑同一命令即续跑。

参数的默认值（都可在 `novelty-probe.json` 中修改，见 6.0）：

- 检索：`sources.openalex.top_n = 25`、`sources.semanticscholar.top_n = 25`、`sources.semanticscholar.max_records = 3000`、`queries.purposes.concurrent.year_from = 2023`、截断词表 `queries.truncation`；
- 合并：`merge.top_k = 20`、`merge.rrf_k = 60`、`merge.bm25 = {k1: 1.2, b: 0.75}`；版本识别 `versions.year_window = 3`、`versions.min_title_words = 5` 与预印本、数据集 DOI 前缀表（`--legacy` 不读配置，固定为前 20 篇、标题至少 5 个词）；
- 引文追踪：`snowball.min_overlap = 2`、`max_forward = 2000`、`top = 20`、`keep = 200`；相似度停用词 `textmatch.stopwords`；
- 比较：`compare.marker_terms`（默认词组 `genai`）；补摘要：`enrich.top = 20`；核验：`verify.landing = true`；
- HTTP：`novelty_probe/http.py` 的 `POLICIES`（按主机：最小间隔、最多尝试次数、退避基数与上限、Retry-After 上限 60 秒、熔断阈值、缓存 TTL、密钥环境变量名），可用 `http.policies` 按主机覆盖。

不可配置的：`merge.py` 的预印本版本规则 `PREPRINT_VERSION_RE`、检索式 id 的 `Q<数字>` 格式（脚本之间的文件名约定）。

## 8. 已定的设计决策（原因见 RUN_LOG 对应步骤）

| 决策 | 原因 | 见 |
|---|---|---|
| 不判断新颖性 | PROJECT.md 规则 a | Step 0 |
| "AI 工具"只指生成式 AI；检索时保留更宽的 AI 说法，筛选时用 LLM、ChatGPT、Gemini、Claude、OpenAI、Anthropic 等关键词判断 | 研究者决定 | Step 2 |
| Semantic Scholar 用 bulk 接口，不用 relevance search | relevance search 不支持布尔和短语；Q2 退回核心词后，前 25 条里 0 条满足原检索式 | Step 3–4 |
| ~~Semantic Scholar 按被引次数取前 25 条~~ → 取回全部命中（最多 3000 条）后本地重排（满足的组数 → BM25 → 被引次数） | 按被引次数偏向老文献；调研实测本地重排后前 25 条全部满足检索式 | Step 4；Step 27 |
| OpenAlex 用 `title_and_abstract.search` | 默认的 `search=` 匹配全文，前 25 条多数在标题和摘要里不满足检索式 | Step 4–5 |
| OpenAlex 的截断词换成完整词 | OpenAlex 的默认检索不支持通配符 | Step 4 |
| concurrent 只取 2023 年起 | 与"只指生成式 AI"一致 | Step 2 |
| 去重：DOI（含预印本版本后缀）、arXiv ID、至少 5 个词的规范化标题；只靠标题合并的组标 `title_linked` | 预印本与正式版的合并；核对时发现过 OSF 版本漏合并 | Step 5 |
| 命中次数 = 命中的"检索式 × 来源"列表数；同一列表里的多个版本只算一次 | 避免版本多的预印本被高估 | Step 6 |
| 候选排序改为 RRF（k=60），BM25 打破并列；OpenAlex 保留 API 的相关度排序 | 按命中次数时前 20 名靠并列决定；两个来源都用本地 BM25 会让缺摘要的参考文献掉到第 23 名 | Step 26–27 |
| 版本识别：标题规范化后相同才自动合并，并要求通过年份、DOI、数据集、来信、摘要等检查；疑似情况只标出 | 预印本标题常带 "(Just accepted by …)"；系统综述去重工具与版本匹配研究都偏向不误并 | Step 26–27 |
| 检索式支持 `AND NOT (…)`，运算符必须大写 | v2 的 narrow AI 噪声；OpenAlex 的小写 not 会把排除变成包含 | Step 26–27 |
| 引文追踪单独成表，不并入检索排序；共被引的过滤词组由研究者决定 | 追踪的目的是找出措辞不同的文献；结果对过滤词组很敏感 | Step 26–61 |
| DOI 核验：Crossref 失败时按 DOI 查 OpenAlex；落地页从 https 跳到 http 时改用 https | arXiv 等 DataCite DOI 需访问 data.crosscite.org；Emerald、IEEE 的 DOI 登记的是 http:// 地址 | Step 24；Step 62–63 |
| DOI 核验 = Crossref 元数据（经 doi.org 内容协商）+ 落地页 | 出版商网站常常拦截脚本；Crossref 能确认 DOI 指向的是哪篇论文 | Step 7–8 |
| ~~证据表"研究问题"面要求研究对象是科研选题~~ → 去掉研究情境后问题相同即记 overlap（研究者的标准） | 研究者不同意原标准 | Step 7；Step 25 |
| 提交信息不放会话链接；`main` 只通过 PR 修改 | 研究者要求 | Step 19–20 |
| 不再为提高 v1、v2 的结果迭代；迭代对象是工具层的准确性、稳定性、适配性 | 研究者决定 | Step 66 |
| 配置用 JSON（`novelty-probe.json`），只写与默认值不同的设置；放参数与词表，不放方法 | 3.9 没有 tomllib；方法变了结果就不可比 | Step 69 |
| `config_hash` 不含 `contact_email` 与 `language` | 两者不影响检索与排序结果 | Step 69 |
| 界面文案用消息表（`novelty_probe/i18n.py`），不用 gettext；数据文件只存结构化结果，展示时按语言生成 | 约百条消息，不值得 .po/.mo 的编译流程；同一份数据可以生成两种语言 | Step 69 |
| 证据表以 JSON 为数据源，Markdown 由它生成；保留 Markdown 入口（`import-md`）；手工改过的 Markdown 不覆盖 | 研究者决定（决策点 1）；结构化核验结果与机器检查放不进 Markdown | Step 69 |
| 单元测试全部禁网；联网接口检查只在 NP_LIVE=1 时运行（6 个请求） | 研究者决定（决策点 3） | Step 69、72 |
| GitHub Actions：Python 3.9–3.13 × Ubuntu / Windows / macOS，只跑离线测试 | 研究者决定（决策点 4）；Windows 与 macOS 在云端测不了 | Step 69 |
| User-Agent 默认是通用的客户端名，不带邮箱 | 助手不代填个人信息；研究者可以在配置里自己填 `contact_email` | Step 69 |

## 9. 已知问题与可改进处

第 9 节原来列出的十个问题已按 `docs/IMPROVEMENT_PLAN.md` 处理（Step 24–64），评估见该文件第 12 节；两张证据表的核验列已用改进后的 `verify.py` 刷新（Step 62–63）。仍需注意：

1. **召回仍依赖人的判断**：v1 的检索式本身检索不到参考文献；两步共被引能把它排到第 1，但只在引用者按情境词（scientists）过滤时如此，换用其他面的词就找不到，而且这一过滤方式是调研时在知道目标的情况下试出的。v2b 的情境（经济学与管理学研究者）中通过过滤的引用者只有 2 篇，共被引几乎没有信息。
2. **剩余噪声**：v2b 前 20 中仍有 1 篇只因 "narrow applications" 命中 narrowing；NOT 短语是看过结果后定的。是否采用 NOT、如何处理剩余用法，由研究者决定（v2b 只是演示，`queries/queries_v2.json` 未改动）。
3. **版本识别只看标题**：标题改动较大的预印本与正式版不会合并（标为待核对或完全漏掉）；没有用到作者信息（原始记录不含作者）。
4. **检索式设计决定排序上限**：v1b 前 20 中仍有通用的文献计量综述和一篇 1993 年的药物设计论文，来自宽泛的方法类检索式和只有 8–9 条命中的 Q3；v2b 前 10 中有 3 篇来自不含 AI 词组的 Q2 的早年文献。
5. **无摘要的记录**：按题目找不到带摘要的其他版本时，仍只能靠题目标注（v1b、v2b 前 20 中各 3 篇）。
6. **落地页核验**：云端被网络策略拦截；本地出版商常对脚本返回 403（可用 `--no-landing` 只核验元数据）。
7. **质量检查是近似**：`qa.py` 用 Porter 词干还原，两个 API 更像 KStem，比例略偏高。
8. **OpenAlex 额度**：云端注入的 key 有每日 1 美元的上限，且可能与其他任务共用；带检索条件的请求每次 0.001 美元。
8a. **S2 的 429**：云端的 S2 key 已确认生效（只有带有效 key 才能访问的数据集接口返回 200），但请求间隔 2 秒时仍有约一半返回 429（Step 65），像是这个 key 的额度同时被别处占用。`search.py` 会按 2、4、8… 秒退避重试，最终成功，只是更慢。
9. **证据检查的边界**：`evidence.py check` 按词序比对引文（大小写、标点不计），能抓出改写和编造的引文，但不判断标注是否合理；中文引号内的转述不检查；作者只在找到 `authors*.json` 时比对。
10. **Crossref 检索源**（决策点 2：实现但默认关闭）属于阶段 3，尚未实现。
11. **待研究者确认**：v2 证据表 rank 8 的"研究问题"面按研究者标准改为 overlap 是助手的推断（Step 25）；v1b、v2b 没有证据表，是否以它们替代 v1、v2 由研究者决定。

## 10. Git 与发布

- **工作流**：在新分支上修改 → 推送 → 开 PR → 合并 → 删除分支。建议在仓库 Settings 里开启 "Automatically delete head branches"。
- **`main` 规则集**：禁止删除、禁止强推、必须走 PR（审批人数 0，bypass 为空）。
- **提交约定**：提交信息不放会话链接或个人信息；作者邮箱用 GitHub 的 noreply 地址。
- **发布新版本**：先改 `CITATION.cff` 的 `version` 和 `date-released`，合并后在 GitHub 上发布 Release，标签与 version 保持一致。如果开通了 Zenodo，它会自动存档并分配 DOI。
- **不要提交 API key**。`.gitignore` 已忽略 `__pycache__/`。

## 11. 交接检查清单

- [ ] 克隆仓库；确认 Python 3.9+
- [ ] 设置 `OPENALEX_API_KEY`（可选 `S2_API_KEY`）
- [ ] `python3 -m unittest discover -s tests -v` 全部通过
- [ ] `python3 scripts/config.py check` 显示检查通过
- [ ] `python3 scripts/search.py --dry-run` 显示 `6/6 queries valid`
- [ ] 冒烟测试通过，并删除 `_smoke` 文件
- [ ] 在 ZCode 中让 GLM 读完 `AGENTS.md`、`PROJECT.md`、`HOWTO.md`、`HANDOFF.md`，并复述三条硬规则
- [ ] 开始新想法前，按 `HOWTO.md` 第 1 节先备份、再清空示例产出
