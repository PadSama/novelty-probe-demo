# HOWTO

**用 novelty-probe 为一个新想法检索文献**

**Probing the literature for a new idea with novelty-probe**

> 给第一次拿到本目录的同学。**你只需要改 `idea/idea.md`**，其余文件由下面的命令（脚本）或 AI 助手（在本目录里运行的 Claude Code）生成。
>
> For first-time users of this directory. **The only file you edit is `idea/idea.md`.** Everything else is produced by the commands below (scripts) or by an AI assistant (Claude Code running in this directory).
>
> 规则见 `PROJECT.md`：不判断新颖性，只找证据；每条文献要有 DOI 或 arXiv ID，否则标 UNVERIFIED；每一步的命令和产出都追加到 `logs/RUN_LOG.md`。
>
> The rules are in `PROJECT.md` (in Chinese): never judge novelty, only collect evidence; every paper needs a DOI or arXiv ID, otherwise it is marked UNVERIFIED; the commands and outputs of every step are appended to `logs/RUN_LOG.md`.

## 流程总览 ｜ Overview

| 步骤<br>Step | 谁来做<br>Done by | 读入<br>Input | 产出<br>Output |
|---|---|---|---|
| T1 写想法<br>Write the idea | 你<br>You | — | `idea/idea.md` |
| T2 拆面与检索式<br>Facets and queries | AI 助手<br>AI assistant | `idea/idea.md` | `facets/facets.md`、`queries/queries.json` |
| T3 检索<br>Search | 脚本<br>Script | `queries/queries.json` | `results/raw/{来源 source}_{检索式 query}.json` |
| T4 合并去重<br>Merge and deduplicate | 脚本<br>Script | `results/raw/` | `results/merged/merged.json`、`results/merged/candidates.csv` |
| T5 证据表与核验<br>Evidence table and verification | 脚本 + AI 助手<br>Scripts + AI assistant | `results/merged/candidates.csv` | `evidence/authors.json`、`evidence/evidence_table.md` |
| T6 差异陈述<br>Difference statement | AI 助手 + 你<br>AI assistant + you | `evidence/evidence_table.md` | `evidence/difference_statement.md` |

- 所有命令都在本目录（项目根目录）下运行。命令按 macOS / Linux 的 shell 写；Windows 建议用 WSL，或把 `python3` 换成 `python`。

  Run every command from this directory (the project root). Commands are written for a macOS / Linux shell; on Windows, use WSL or replace `python3` with `python`.

- **AI 助手步骤**：在本目录启动 Claude Code，把对应的提示词原样粘贴进去（每个提示词都有中文和英文两个版本，任选其一）。也可以手工完成，按提示词里的格式写文件。

  **AI assistant steps**: start Claude Code in this directory and paste the corresponding prompt as is (each prompt comes in a Chinese and an English version; use either). You can also do these steps by hand, writing the files in the format the prompt describes.

- **脚本步骤**：每条命令都包在 `python3 scripts/logrun.py "<步骤名>" -- …` 里。它照常运行命令，同时把命令和输出追加到 `logs/RUN_LOG.md`。

  **Script steps**: every command is wrapped in `python3 scripts/logrun.py "<step name>" -- …`, which runs the command as usual and appends the command and its output to `logs/RUN_LOG.md`.

## 0. 准备（只做一次）｜ Setup (one-time)

**Python 3.9 或更高**。只用标准库，不需要安装任何包。

**Python 3.9 or later.** The scripts use only the standard library; nothing needs to be installed.

```bash
python3 --version
```

**网络**：需要能访问下列域名。在自己电脑上运行通常不用处理；在 Claude Code 云环境中运行，要在环境设置的 Network access 里放行。

**Network**: the domains below must be reachable. On your own computer this usually needs no action; in a Claude Code cloud environment, allow them under Network access in the environment settings.

| 域名<br>Domain | 用于<br>Used for |
|---|---|
| `api.openalex.org` | T3 检索、T5 查作者<br>T3 search, T5 author lookup |
| `api.semanticscholar.org` | T3 检索<br>T3 search |
| `doi.org`、`api.crossref.org` | T5 DOI 核验<br>T5 DOI verification |
| `data.crosscite.org`（可选 optional） | 核验 arXiv 等 DataCite 登记的 DOI<br>Verifying DOIs registered with DataCite, such as arXiv DOIs |
| 各出版商域名（可选）<br>Publisher domains (optional) | 核验落地页标题；不放行时显示 BLOCKED，不影响 Crossref 核验<br>Checking landing-page titles; without access the result reads BLOCKED, which does not affect the Crossref check |

**API key**（不要写进任何文件，也不要提交到仓库）：

**API keys** (never write them into any file or commit them to the repository):

- **OpenAlex：强烈建议申请**免费 key：https://help.openalex.org/api/authentication/ 。不带 key 时，与同一出口 IP 的所有人共用每日免费额度，云环境里常常已经用完（返回 429 "Insufficient budget"）。在自己电脑上用环境变量设置；云环境里加在 Network secrets 中，不需要环境变量。

  **OpenAlex: strongly recommended.** Get a free key at https://help.openalex.org/api/authentication/ . Without a key, you share a daily free budget with everyone on the same outgoing IP address, and in cloud environments it is often already used up (HTTP 429 "Insufficient budget"). On your own computer, set it as an environment variable; in a cloud environment, add it under Network secrets instead.

```bash
export OPENALEX_API_KEY="你的 key / your key"
```

- **Semantic Scholar：可选**，申请地址 https://www.semanticscholar.org/product/api#api-key-form 。不带 key 时共用匿名限流池，偶尔返回 429。脚本会自动重试，仍失败的可以单独补跑（见 T3）。

  **Semantic Scholar: optional.** Apply at https://www.semanticscholar.org/product/api#api-key-form . Without a key, you share an anonymous rate-limit pool and occasionally get HTTP 429. The script retries automatically; anything that still fails can be re-run on its own (see T3).

```bash
export S2_API_KEY="你的 key / your key"
```

## 1. 清空示例产出 ｜ Clear the example outputs

目录里保留着教程示例（v1、v2）的产出。开始自己的想法前要先清空，否则旧结果会混进新结果。

This directory still holds the outputs of the tutorial example (v1 and v2). Clear them before starting your own idea; otherwise old results will mix with new ones.

可选：先把示例备份到 `examples/`。

Optional: back up the example to `examples/` first.

```bash
mkdir -p examples && cp -r facets queries results evidence logs examples/
```

清空旧产出（`.gitkeep` 是隐藏文件，不会被删除）：

Delete the old outputs (`.gitkeep` files are hidden and are not deleted):

```bash
rm -f facets/*.md queries/*.json results/raw/*.json results/merged/*.json results/merged/*.csv evidence/*.md evidence/*.json idea/idea_v*.md
```

重置日志：

Reset the log:

```bash
printf '# RUN_LOG\n\n> 只追加，不改写。每条记录：时间 / 步骤 / 命令 / 产出文件。\n' > logs/RUN_LOG.md
```

## 2. T1 写想法（你）｜ T1 Write the idea (you)

用一两句话写清：谁、用什么、可能带来什么结果、打算用什么数据，直接覆盖 `idea/idea.md`。本教程用的原文：

In one or two sentences, state who does what with which tool, what outcome you expect, and what data you plan to use, and overwrite `idea/idea.md` with it. The idea used in this tutorial:

> 我注意到身边越来越多人用 AI 做研究。我想研究：科研人员使用 AI 工具，会不会让整个学科的选题变窄？打算用大规模论文数据来测。
>
> I have noticed more and more people around me using AI for research. I want to study whether researchers' use of AI tools narrows the range of research topics across a whole discipline, using large-scale publication data.

## 3. T2 拆面与检索式（AI 助手）｜ T2 Facets and queries (AI assistant)

把下面任一版本的提示词粘贴给 Claude Code：

Paste either version of the prompt below into Claude Code:

```text
读 idea/idea.md。按 PROJECT.md 的规则：
1) 拆成五个面写到 facets/facets.md：研究问题、作用机制、研究情境、数据与方法、预期发现；
2) 每个面给 3–5 个英文检索词（含同义词、相邻学科说法）；
3) 组合 6 条检索式写到 queries/queries.json，字段：id（Q1–Q6）, facets_used, query, purpose（component / application / method / concurrent）。
检索式格式（scripts/search.py 只认这种写法）：用 AND 连接若干个括号组，括号内只用 OR；短语加英文双引号；不用截断符 *、NOT、嵌套括号和逗号。
完成后把产出文件追加到 logs/RUN_LOG.md。
```

```text
Read idea/idea.md. Following the rules in PROJECT.md:
1) Break the idea into five facets and write them to facets/facets.md: research question, mechanism, context, data and methods, expected findings;
2) Give each facet 3–5 English search terms, including synonyms and the terms used in adjacent disciplines;
3) Combine them into 6 queries in queries/queries.json with the fields id (Q1–Q6), facets_used, query, and purpose (component / application / method / concurrent).
Query format (the only format scripts/search.py accepts): parenthesized groups joined by AND, with only OR inside each group; phrases in English double quotes; no truncation (*), NOT, nested parentheses or commas.
When done, append the output files to logs/RUN_LOG.md.
```

助手可能会就范围提问（教程里问过"AI 工具"是否只指生成式 AI），由你决定。

The assistant may ask you about scope (in the tutorial it asked whether "AI tools" meant generative AI only); those decisions are yours.

检查检索式语法（不联网，不消耗额度）：

Check the query syntax (offline; no API budget used):

```bash
python3 scripts/search.py --dry-run
```

最后一行应为 `6/6 queries valid`。有 INVALID 的，把报错发给助手，让它修改 `queries/queries.json`。

The last line should read `6/6 queries valid`. If any query is INVALID, give the error to the assistant and have it fix `queries/queries.json`.

## 4. T3 检索（脚本）｜ T3 Search (script)

```bash
python3 scripts/logrun.py "T3 检索" -- python3 scripts/search.py
```

- 每条检索式分别查 OpenAlex（标题 + 摘要，按相关度）和 Semantic Scholar（bulk 检索，标题 + 摘要，按被引次数），各存前 25 条到 `results/raw/`。

  Each query is run against OpenAlex (titles and abstracts, ranked by relevance) and Semantic Scholar (bulk search on titles and abstracts, ranked by citation count); the top 25 records from each are saved to `results/raw/`.

- purpose 为 concurrent 的检索式只取 2023 年起的文献。要改年份，修改 `scripts/search.py` 中的 `CONCURRENT_FROM_YEAR`。

  Queries with the purpose concurrent only return papers from 2023 onwards. To change the year, edit `CONCURRENT_FROM_YEAR` in `scripts/search.py`.

- 终端每行是一个"检索式 × 来源"：`total_hits` 是 API 报告的命中数，`saved` 是保存条数，`no_id` 是既无 DOI 也无 arXiv ID 的条数。

  Each line of terminal output is one query × source: `total_hits` is the hit count reported by the API, `saved` is the number of records kept, and `no_id` is the number of records with neither a DOI nor an arXiv ID.

有 FAILED 的行，先按原因处理（见"常见问题"），再只补跑失败的部分，例如：

For lines marked FAILED, fix the cause first (see Troubleshooting), then re-run only what failed, for example:

```bash
python3 scripts/logrun.py "T3 补跑" -- python3 scripts/search.py --ids Q3,Q4 --sources semanticscholar
```

## 5. T4 合并去重（脚本）｜ T4 Merge and deduplicate (script)

```bash
python3 scripts/logrun.py "T4 合并去重" -- python3 scripts/merge.py
```

按 DOI、arXiv ID、规范化标题去重（预印本平台的版本 DOI 视为同一篇），输出：

Records are deduplicated by DOI, arXiv ID and normalized title (versioned DOIs on preprint servers count as one work). Outputs:

- `results/merged/merged.json`：去重后的全部文献。每篇带出处 `raw_refs`，可回查原始记录。

  `results/merged/merged.json`: all deduplicated works. Each work carries `raw_refs`, pointing back to its raw records.

- `results/merged/candidates.csv`：按命中次数（命中的"检索式 × 来源"数）取前 20 篇，Excel 可直接打开。

  `results/merged/candidates.csv`: the top 20 works by hits (the number of query × source result lists containing the work); opens directly in Excel.

注意：命中次数只反映两个来源是否都检索到，不代表与研究问题的相关度。

Note: hits only show whether both sources found a work; they do not measure relevance to your research question.

## 6. T5 证据表与核验（脚本 + AI 助手）｜ T5 Evidence table and verification (scripts + AI assistant)

查作者（检索结果不含作者字段）：

Look up authors (the search results do not include authors):

```bash
python3 scripts/logrun.py "T5 查作者" -- python3 scripts/authors.py --top 10
```

把下面任一版本的提示词粘贴给 Claude Code：

Paste either version of the prompt below into Claude Code:

```text
读 results/merged/candidates.csv 前 10 篇的摘要（作者见 evidence/authors.json），对照 facets/facets.md，逐面标 overlap / differ / unknown，写到 evidence/evidence_table.md。
表格列：rank, 作者, 年份, 题目, DOI/arXiv, 研究问题, 作用机制, 研究情境, 数据与方法, 预期发现, verified。
DOI/arXiv 列写成 doi:<DOI>，有 arXiv ID 时加上 " · arXiv:<ID>"；verified 列先写"待核验"。
在文件开头写明标注规则，在表下逐篇写判定依据并引用摘要原文。不判断新颖性；把产出文件追加到 logs/RUN_LOG.md。
```

```text
Read the abstracts of the top 10 works in results/merged/candidates.csv (authors are in evidence/authors.json). Compare each with facets/facets.md, label every facet overlap / differ / unknown, and write the result to evidence/evidence_table.md.
Table columns: rank, Authors, Year, Title, DOI/arXiv, Research question, Mechanism, Context, Data and methods, Expected findings, verified.
Write the DOI/arXiv column as doi:<DOI>, adding " · arXiv:<ID>" when there is an arXiv ID; put "pending" in the verified column for now.
State the labeling rules at the top of the file, and below the table give the evidence for each paper, quoting the abstract. Do not judge novelty; append the output files to logs/RUN_LOG.md.
```

核验 DOI，结果写回 verified 列：

Verify the DOIs; the results are written back into the verified column:

```bash
python3 scripts/logrun.py "T5 DOI 核验" -- python3 scripts/verify.py
```

verified 列格式为"Crossref 结果；落地页结果"。"Crossref HTTP 200 · 题目一致"表示 DOI 有效，且指向表中这篇；BLOCKED 表示该域名未放行；没有 DOI 的行写 UNVERIFIED。

The verified column reads "Crossref result；landing-page result" (落地页 = landing page). "Crossref HTTP 200 · 题目一致" (title matches) means the DOI is valid and points to the paper in the table; 题目不一致 means the titles differ; BLOCKED means that domain is not allowed; rows without a DOI read UNVERIFIED.

## 7. T6 差异陈述（AI 助手 + 你）｜ T6 Difference statement (AI assistant + you)

把下面任一版本的提示词粘贴给 Claude Code：

Paste either version of the prompt below into Claude Code:

```text
生成 evidence/difference_statement.md，三节：
1. 最接近的三篇：从 evidence/evidence_table.md 原样复制整行，由你按明确的规则选出，并把规则写在表下；
2. 本想法在哪一个面上不同、差多大：留空，由我填写；
3. 审稿人最可能说"已被做过"的一条理由及其文献：留空，由我填写。
把产出文件追加到 logs/RUN_LOG.md。
```

```text
Create evidence/difference_statement.md with three sections:
1. The three closest papers: copy their rows verbatim from evidence/evidence_table.md, chosen by you according to an explicit rule, and state the rule below the table;
2. On which facet this idea differs and by how much: leave blank for me to fill in;
3. The single reason a reviewer would most likely give for "this has already been done", with its reference: leave blank for me to fill in.
Append the output file to logs/RUN_LOG.md.
```

然后你自己填写第 2、3 节。

Then fill in sections 2 and 3 yourself.

## 8. 换一个面再跑一轮（可选）｜ Another round with a changed facet (optional)

教程的 v2 就是这样做的：想法另存为新文件，所有产出加版本后缀，不覆盖上一轮。

This is how the tutorial's v2 was made: save the idea as a new file and give every output a version suffix, so the previous round is not overwritten.

```bash
cp idea/idea.md idea/idea_v2.md
```

修改 `idea/idea_v2.md`，再用 T2 的提示词让 AI 助手生成 `facets/facets_v2.md` 和 `queries/queries_v2.json`（把提示词里的文件名都换成 `_v2` 版本）。然后依次运行：

Edit `idea/idea_v2.md`, then use the T2 prompt to have the assistant produce `facets/facets_v2.md` and `queries/queries_v2.json` (change every file name in the prompt to its `_v2` version). Then run, in order:

```bash
python3 scripts/search.py --queries queries/queries_v2.json --dry-run
```

```bash
python3 scripts/logrun.py "T3 v2 检索" -- python3 scripts/search.py --queries queries/queries_v2.json --suffix _v2
```

```bash
python3 scripts/logrun.py "T4 v2 合并去重" -- python3 scripts/merge.py --suffix _v2
```

```bash
python3 scripts/logrun.py "T5 v2 查作者" -- python3 scripts/authors.py --top 10 --candidates results/merged/candidates_v2.csv --out evidence/authors_v2.json
```

用 T5 的提示词让 AI 助手把证据表写到 `evidence/evidence_table_v2.md`（输入换成 `candidates_v2.csv`、`authors_v2.json`、`facets_v2.md`），然后：

Use the T5 prompt to have the assistant write the evidence table to `evidence/evidence_table_v2.md` (with `candidates_v2.csv`, `authors_v2.json` and `facets_v2.md` as inputs), then:

```bash
python3 scripts/logrun.py "T5 v2 DOI 核验" -- python3 scripts/verify.py --table evidence/evidence_table_v2.md
```

## 常见问题 ｜ Troubleshooting

| 现象<br>Symptom | 原因<br>Cause | 处理<br>Fix |
|---|---|---|
| `FAILED: network error: Tunnel connection failed: 403`，或 `BLOCKED at <域名>`<br>`FAILED: network error: Tunnel connection failed: 403`, or `BLOCKED at <domain>` | 云环境未放行该域名<br>The cloud environment does not allow that domain | 在 Network access 中放行（见"准备"）<br>Allow it under Network access (see Setup) |
| `HTTP 429: Insufficient budget …`（OpenAlex） | 没带 key，共用的每日额度已用完<br>No key, and the shared daily budget is used up | 设置 OpenAlex key 后重跑<br>Set an OpenAlex key and re-run |
| `HTTP 429: Too Many Requests …`（Semantic Scholar） | 匿名限流池繁忙<br>The anonymous rate-limit pool is busy | 等几分钟后用 `--ids`、`--sources` 补跑，或申请 S2 key<br>Wait a few minutes and re-run with `--ids` / `--sources`, or get an S2 key |
| `INVALID: 未登记的截断词 …`、`不支持括号外的 OR` 等<br>`INVALID: 未登记的截断词 …` (unregistered truncation), `不支持括号外的 OR` (OR outside parentheses), etc. | 检索式写法不符合要求<br>The query does not follow the required format | 按 T2 的格式修改 `queries/queries.json`，再跑 `--dry-run`<br>Fix `queries/queries.json` to the T2 format and run `--dry-run` again |
| `results/raw/ 中同一来源混有不同检索方式的结果`<br>(results from different search methods mixed for one source) | 混有旧脚本或旧想法留下的结果<br>Leftover results from an older script or a previous idea | 按第 1 步清空 `results/raw/`，重跑 T3<br>Clear `results/raw/` as in step 1 and re-run T3 |
| 某条检索式在某个来源命中 0 条<br>A query returns 0 hits from one source | 组合太严<br>The combination is too strict | 可以接受；或让助手放宽这条检索式<br>Acceptable; or ask the assistant to loosen that query |
| verified 列为 `Crossref BLOCKED at data.crosscite.org`<br>The verified column reads `Crossref BLOCKED at data.crosscite.org` | arXiv 等 DataCite 登记的 DOI<br>A DOI registered with DataCite, such as an arXiv DOI | 放行 `data.crosscite.org` 后重跑 `verify.py`<br>Allow `data.crosscite.org` and re-run `verify.py` |

## 目录速查 ｜ Directory reference

| 路径<br>Path | 内容<br>Contents |
|---|---|
| `README.md` | 英文项目介绍<br>Project overview in English |
| `PROJECT.md` | 助手的角色与三条硬规则（中文）<br>The assistant's role and three rules (Chinese) |
| `idea/idea.md` | 你的想法（唯一需要你改的文件）<br>Your idea (the only file you edit) |
| `facets/`、`queries/` | T2 产出<br>T2 outputs |
| `results/raw/`、`results/merged/` | T3、T4 产出<br>T3 and T4 outputs |
| `evidence/` | T5、T6 产出<br>T5 and T6 outputs |
| `logs/RUN_LOG.md` | 运行日志<br>Run log |
| `scripts/search.py` | T3 检索（`--dry-run` 检查语法；`--ids`、`--sources` 补跑；`--queries`、`--suffix` 用于新一轮）<br>T3 search (`--dry-run` checks syntax; `--ids`, `--sources` re-run failures; `--queries`, `--suffix` for a new round) |
| `scripts/merge.py` | T4 合并去重（`--suffix`）<br>T4 merge and deduplicate (`--suffix`) |
| `scripts/authors.py` | T5 查作者（`--top`、`--candidates`、`--out`）<br>T5 author lookup (`--top`, `--candidates`, `--out`) |
| `scripts/verify.py` | T5 DOI 核验（`--table`）<br>T5 DOI verification (`--table`) |
| `scripts/logrun.py` | 运行一条命令，同时写入 `logs/RUN_LOG.md`<br>Runs a command and records it in `logs/RUN_LOG.md` |
