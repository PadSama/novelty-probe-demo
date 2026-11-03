# HOWTO

**用 novelty-probe 为一个新想法检索文献**

**Probing the literature for a new idea with novelty-probe**

> 给第一次拿到本目录的同学。**你只需要改 `idea/idea.md`**，其余文件由下面的命令（脚本）或 AI 编程助手（在本目录里运行，如 ZCode + GLM、Claude Code）生成。
>
> For first-time users of this directory. **The only file you edit is `idea/idea.md`.** Everything else is produced by the commands below (scripts) or by an AI coding assistant running in this directory (for example ZCode with GLM, or Claude Code).
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
| T5 证据表与核验<br>Evidence table and verification | 脚本 + AI 助手<br>Scripts + AI assistant | `results/merged/candidates.csv` | `evidence/authors.json`、`evidence/enrichment.json`、`evidence/evidence_table.md` |
| T5b 引文追踪（可选）<br>Citation chasing (optional) | 脚本 + 你<br>Script + you | `evidence/evidence_table.md` | `results/raw/chase_*.json`、`results/merged/chase_*.csv` |
| T6 差异陈述<br>Difference statement | AI 助手 + 你<br>AI assistant + you | `evidence/evidence_table.md` | `evidence/difference_statement.md` |

- 所有命令都在本目录（项目根目录）下运行。命令按 macOS / Linux 的 shell 写；Windows 建议用 WSL，或把 `python3` 换成 `python`。

  Run every command from this directory (the project root). Commands are written for a macOS / Linux shell; on Windows, use WSL or replace `python3` with `python`.

- **AI 助手步骤**：在本目录启动你的 AI 编程助手（如 ZCode + GLM、Claude Code），先让它读 `AGENTS.md`，再把对应的提示词原样粘贴进去（每个提示词都有中文和英文两个版本，任选其一）。也可以手工完成，按提示词里的格式写文件。

  **AI assistant steps**: start your AI coding assistant in this directory (for example ZCode with GLM, or Claude Code), have it read `AGENTS.md` first, then paste the corresponding prompt as is (each prompt comes in a Chinese and an English version; use either). You can also do these steps by hand, writing the files in the format the prompt describes.

- **脚本步骤**：每条命令都包在 `python3 scripts/logrun.py "<步骤名>" -- …` 里。它照常运行命令，同时把命令和输出追加到 `logs/RUN_LOG.md`。

  **Script steps**: every command is wrapped in `python3 scripts/logrun.py "<step name>" -- …`, which runs the command as usual and appends the command and its output to `logs/RUN_LOG.md`.

## 0. 准备（只做一次）｜ Setup (one-time)

**Python 3.9 或更高**。只用标准库，不需要安装任何包。

**Python 3.9 or later.** The scripts use only the standard library; nothing needs to be installed.

```bash
python3 --version
```

**离线自检**（几秒，不联网）：全部显示 OK，说明环境和脚本都正常。

**Offline self-test** (a few seconds, no network): if every test reports OK, your environment and the scripts work.

```bash
python3 -m unittest discover -s tests -v
```

测试不联网（试图访问外网会直接报错）；6 项联网的接口检查显示 skipped，见"常见问题"上方的说明。

The tests never use the network (any attempt fails loudly); the 6 live interface checks show as skipped (see the note above Troubleshooting).

**配置**：项目根目录的 `novelty-probe.json` 只写与内置默认值不同的设置。查看全部设置与当前配置的指纹（config_hash，写进每个输出文件）、检查写法：

**Configuration**: `novelty-probe.json` in the project root holds only the settings that differ from the built-in defaults. To see every setting and the configuration fingerprint (config_hash, recorded in every output file), or to check the file:

```bash
python3 scripts/config.py show
```

```bash
python3 scripts/config.py check
```

常改的设置：`language`（界面语言）、`queries.purposes.concurrent.year_from`（concurrent 检索式的起始年份）、`queries.truncation`（截断词对应的完整词）、`sources.<来源>.top_n` 与 `enabled`、`merge.top_k`、`facets`（面的名称与中英文标签）、`compare.marker_terms`。列表整体替换；要在默认列表后追加，写 `<键>_extend`，例如 `"versions": {"preprint_doi_prefixes_extend": ["10.xxxx/"]}`。改参数属于研究设计，由你决定。

Settings you are most likely to change: `language` (interface language), `queries.purposes.concurrent.year_from` (start year of concurrent queries), `queries.truncation` (full words for truncated terms), `sources.<source>.top_n` and `enabled`, `merge.top_k`, `facets` (facet names with Chinese and English labels), `compare.marker_terms`. Lists are replaced as a whole; to append to a default list, use `<key>_extend`, for example `"versions": {"preprint_doi_prefixes_extend": ["10.xxxx/"]}`. Changing parameters is a research-design decision, and it is yours.

**界面语言**：帮助、报错、verified 列默认中文；加 `--lang en`、设环境变量 `NP_LANG=en`，或在配置里写 `"language": "en"`，即改为英文。

**Interface language**: help, error messages and the verified column are in Chinese by default; add `--lang en`, set the environment variable `NP_LANG=en`, or put `"language": "en"` in the configuration to switch to English.

```bash
export NP_LANG=en
```

**项目目录**：脚本从当前目录向上找 `novelty-probe.json` 或 `PROJECT.md`，以它所在的目录为项目根目录；一份脚本可以服务多个项目目录，也可以用 `--root <目录>` 或环境变量 `NOVELTY_PROBE_ROOT` 指定。

**Project folder**: the scripts look upwards from the current folder for `novelty-probe.json` or `PROJECT.md` and use that folder as the project root; one copy of the scripts can serve several project folders, or you can name one with `--root <folder>` or the environment variable `NOVELTY_PROBE_ROOT`.

**网络**：需要能访问下列域名。在自己电脑上运行通常不用处理；在云端沙箱环境（如 Claude Code 的云环境）中运行，要在环境设置的 Network access 里放行。

**Network**: the domains below must be reachable. On your own computer this usually needs no action; in a cloud sandbox (such as a Claude Code cloud environment), allow them under Network access in the environment settings.

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

- **Semantic Scholar：可选**，申请地址 https://www.semanticscholar.org/product/api#api-key-form 。不带 key 时共用匿名限流池，偶尔返回 429。有 key 时的限额是每秒 1 个请求、所有接口合计，脚本对每个发往 S2 的请求（含翻页与重试）自动节流。脚本会自动重试，仍失败的可以单独补跑（见 T3）。

  **Semantic Scholar: optional.** Apply at https://www.semanticscholar.org/product/api#api-key-form . Without a key, you share an anonymous rate-limit pool and occasionally get HTTP 429. With a key, the limit is 1 request per second across all endpoints, and the script throttles every Semantic Scholar request (including pages and retries) accordingly. The script retries automatically; anything that still fails can be re-run on its own (see T3).

```bash
export S2_API_KEY="你的 key / your key"
```

## 1. 清空示例产出 ｜ Clear the example outputs

目录里保留着教程示例（v1、v2）的产出。开始自己的想法前要先清空，否则旧结果会混进新结果。

This directory still holds the outputs of the tutorial example (v1 and v2). Clear them before starting your own idea; otherwise old results will mix with new ones.

教程示例的副本已经在 `examples/tutorial/` 里（离线自检从那里读取），不必另行备份。

A copy of the tutorial example is already kept in `examples/tutorial/` (the offline self-test reads from there), so no backup is needed.

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

把下面任一版本的提示词粘贴给 AI 助手：

Paste either version of the prompt below into the AI assistant:

```text
读 idea/idea.md。按 PROJECT.md 的规则：
1) 拆成五个面写到 facets/facets.md：研究问题、作用机制、研究情境、数据与方法、预期发现；
2) 每个面给 3–5 个英文检索词（含同义词、相邻学科说法）；
3) 组合 6 条检索式写到 queries/queries.json，字段：id（Q1–Q6）, facets_used, query, purpose（component / application / method / concurrent）。
检索式格式（scripts/search.py 只认这种写法）：用 AND 连接若干个括号组，括号内只用 OR；短语加英文双引号；运算符一律大写；不用截断符 *、嵌套括号和逗号。需要排除某些说法时，在最后加 AND NOT ("…" OR "…")。
完成后把产出文件追加到 logs/RUN_LOG.md。
```

```text
Read idea/idea.md. Following the rules in PROJECT.md:
1) Break the idea into five facets and write them to facets/facets.md: research question, mechanism, context, data and methods, expected findings;
2) Give each facet 3–5 English search terms, including synonyms and the terms used in adjacent disciplines;
3) Combine them into 6 queries in queries/queries.json with the fields id (Q1–Q6), facets_used, query, and purpose (component / application / method / concurrent).
Query format (the only format scripts/search.py accepts): parenthesized groups joined by AND, with only OR inside each group; phrases in English double quotes; operators in upper case; no truncation (*), nested parentheses or commas. To exclude some phrasings, append AND NOT ("…" OR "…") at the end.
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

- 每条检索式分别查 OpenAlex（标题 + 摘要，按 API 的相关度）和 Semantic Scholar（bulk 检索，标题 + 摘要），各存前 25 条到 `results/raw/`。S2 的 bulk 接口不按相关度排序，脚本取回全部命中（最多 3000 条）后在本地重排：满足的 AND 组数 → BM25 → 被引次数；没有摘要的记录单独排序并按比例穿插，标题相同的只留一条。

  Each query is run against OpenAlex (titles and abstracts, ranked by the API's relevance score) and Semantic Scholar (bulk search on titles and abstracts); the top 25 records from each are saved to `results/raw/`. S2's bulk endpoint does not rank by relevance, so the script fetches all hits (up to 3,000) and re-ranks them locally: number of AND groups matched, then BM25, then citation count. Records without an abstract are ranked separately and interleaved in proportion, and duplicate titles are kept once.

- 排除组 `AND NOT (…)`：OpenAlex 原样发送（必须大写 NOT，小写会被当成普通词，把排除变成必须包含；脚本发现 OpenAlex 没有按 NOT 解析时会报错），S2 译为 `+ -(…)`。

  Exclusion groups `AND NOT (…)` are sent to OpenAlex unchanged (NOT must be upper case: OpenAlex treats a lower-case not as an ordinary word and turns the exclusion into a requirement; the script stops if OpenAlex did not parse the NOT), and translated to `+ -(…)` for S2.

- purpose 为 concurrent 的检索式只取 2023 年起的文献。要改年份，修改 `scripts/search.py` 中的 `CONCURRENT_FROM_YEAR`。

  Queries with the purpose concurrent only return papers from 2023 onwards. To change the year, edit `CONCURRENT_FROM_YEAR` in `scripts/search.py`.

- 终端每行是一个"检索式 × 来源"：`total_hits` 是 API 报告的命中数，`saved` 是保存条数，`no_id` 是既无 DOI 也无 arXiv ID 的条数。

  Each line of terminal output is one query × source: `total_hits` is the hit count reported by the API, `saved` is the number of records kept, and `no_id` is the number of records with neither a DOI nor an arXiv ID.

有 FAILED 的行，先按原因处理（见"常见问题"），再只补跑失败的部分，例如：

For lines marked FAILED, fix the cause first (see Troubleshooting), then re-run only what failed, for example:

```bash
python3 scripts/logrun.py "T3 补跑" -- python3 scripts/search.py --ids Q3,Q4 --sources semanticscholar
```

网络层：所有联网脚本都接受 `--http-mode cache`（先查本地缓存 `.cache/http`，省额度、少挨限流）与 `--refresh`（忽略缓存）；默认 `live`。OpenAlex 对格式错误的检索式不报错而静默改写（例如未配对的引号），脚本会核对它返回的解析结果，发现不一致就报错、不保存。

Network layer: every networked script accepts `--http-mode cache` (check the local cache `.cache/http` first, saving budget and rate-limit hits) and `--refresh` (ignore the cache); the default is `live`. OpenAlex silently rewrites malformed queries (for example an unbalanced quote) instead of reporting an error; the script checks the parse OpenAlex returns and stops without saving if it does not match.

可选：检查检索质量（每个结果文件中，标题 + 摘要满足原检索式的记录有多少；用 Porter 词干还原近似两个 API 的匹配，比例略偏高）：

Optional: check search quality (how many records in each result file satisfy the original query in their title and abstract; Porter stemming approximates the APIs' matching, so the shares run slightly high):

```bash
python3 scripts/logrun.py "T3 质量检查" -- python3 scripts/qa.py
```

## 5. T4 合并去重（脚本）｜ T4 Merge and deduplicate (script)

```bash
python3 scripts/logrun.py "T4 合并去重" -- python3 scripts/merge.py
```

按 DOI、arXiv ID 去重（预印本平台的版本 DOI 视为同一篇），再识别同一研究的不同版本：规范化标题相同（去掉 "(Just accepted by …)" 之类的发表状态括注）且通过一组保守的检查（年份相差 ≤3、不是两个不同的正式发表 DOI、不是数据集、不是 "Re:" 之类的来信等）才自动合并，疑似情况只标出（`review` 字段）供你核对。年份取正式发表版本，最早版本记在 `year_first`。输出：

Records are deduplicated by DOI and arXiv ID (versioned DOIs on preprint servers count as one work); then versions of the same work are linked: titles that match after normalization (dropping publication-status notes such as "(Just accepted by …)") are merged only if a set of conservative checks passes (years at most 3 apart, not two different journal DOIs, not a dataset, not a "Re:" letter, and so on); doubtful pairs are only flagged (the `review` field) for you to check. The year is that of the version of record; the earliest version's year is kept in `year_first`. Outputs:

- `results/merged/merged.json`：去重后的全部文献。每篇带出处 `raw_refs`，可回查原始记录。

  `results/merged/merged.json`: all deduplicated works. Each work carries `raw_refs`, pointing back to its raw records.

- `results/merged/candidates.csv`：前 20 篇，按倒数排名融合（RRF：在各"检索式 × 来源"列表中的名次 r，累加 1/(60 + r)）排序，BM25（全部检索词）打破并列；`hits`、`n_conform`（本地判断满足几条检索式）只作参考。Excel 可直接打开。

  `results/merged/candidates.csv`: the top 20 works, ranked by reciprocal rank fusion (RRF: for each query × source list in which the work appears at rank r, add 1/(60 + r)), with BM25 over all query terms breaking ties; `hits` and `n_conform` (how many queries the work satisfies, checked locally) are shown for reference. Opens directly in Excel.

注意：排名反映检索式与文本的匹配，不代表与研究问题的相关度。要复现教程 v1、v2 当时的合并方法（按命中次数排序），加 `--legacy`。

Note: the ranking reflects how well the text matches the queries, not relevance to your research question. To reproduce the merge method used for the tutorial's v1 and v2 (ranking by hits), add `--legacy`.

## 6. T5 证据表与核验（脚本 + AI 助手）｜ T5 Evidence table and verification (scripts + AI assistant)

查作者（检索结果不含作者字段）：

Look up authors (the search results do not include authors):

```bash
python3 scripts/logrun.py "T5 查作者" -- python3 scripts/authors.py --top 10
```

为没有摘要的候选从同一研究的其他版本（如 arXiv 预印本）补摘要，连同来源写到 `evidence/enrichment.json`：

For candidates without an abstract, fetch one from another version of the same work (such as its arXiv preprint); the abstracts and their sources go to `evidence/enrichment.json`:

```bash
python3 scripts/logrun.py "T5 补摘要" -- python3 scripts/enrich.py --top 20
```

把下面任一版本的提示词粘贴给 AI 助手：

Paste either version of the prompt below into the AI assistant:

```text
读 results/merged/candidates.csv 前 10 篇的摘要（作者见 evidence/authors.json），对照 facets/facets.md，逐面标 overlap / differ / unknown，写到 evidence/evidence_table.md。
表格列：rank, 作者, 年份, 题目, DOI/arXiv, 研究问题, 作用机制, 研究情境, 数据与方法, 预期发现, verified。
DOI/arXiv 列写成 doi:<DOI>，有 arXiv ID 时加上 " · arXiv:<ID>"；verified 列先写"待核验"。
在文件开头写明标注规则，在表下逐篇写判定依据（每篇以 **rank · merged_id** 开头）并引用摘要原文。候选本身没有摘要时，可以用 evidence/enrichment.json 中补到的摘要，并注明来源（DOI）。
写完后运行 python3 scripts/evidence.py check evidence/evidence_table.md，按报告修改，直到没有问题。不判断新颖性；把产出文件追加到 logs/RUN_LOG.md。
```

```text
Read the abstracts of the top 10 works in results/merged/candidates.csv (authors are in evidence/authors.json). Compare each with facets/facets.md, label every facet overlap / differ / unknown, and write the result to evidence/evidence_table.md.
Table columns: rank, Authors, Year, Title, DOI/arXiv, Research question, Mechanism, Context, Data and methods, Expected findings, verified.
Write the DOI/arXiv column as doi:<DOI>, adding " · arXiv:<ID>" when there is an arXiv ID; put "pending" in the verified column for now.
State the labeling rules at the top of the file, and below the table give the evidence for each paper (each starting with **rank · merged_id**), quoting the abstract. If a candidate has no abstract, you may use the abstract in evidence/enrichment.json, citing its source (DOI).
When done, run python3 scripts/evidence.py check evidence/evidence_table.md and fix what it reports until no problems remain. Do not judge novelty; append the output files to logs/RUN_LOG.md.
```

检查证据表（不联网）：取值是否合法；DOI、arXiv ID 是否来自检索结果（规则 2）；题目、年份、作者是否与检索结果一致；判定依据里引号内的英文是否为摘要原文（大小写、标点不计；"..." 表示省略）。有问题时退出码为 1，并逐条列出：

Check the evidence table (no network): labels are valid; DOIs and arXiv IDs come from the search results (rule 2); titles, years and authors match the search results; quoted English text in the evidence is verbatim from the abstract (case and punctuation ignored; "..." marks an omission). Problems are listed one by one, with exit code 1:

```bash
python3 scripts/logrun.py "T5 证据表检查" -- python3 scripts/evidence.py check evidence/evidence_table.md
```

核验 DOI，结果写回 verified 列：

Verify the DOIs; the results are written back into the verified column:

```bash
python3 scripts/logrun.py "T5 DOI 核验" -- python3 scripts/verify.py
```

verified 列格式为"Crossref 结果；落地页结果"。"Crossref HTTP 200 · 题目一致"表示 DOI 有效，且指向表中这篇；BLOCKED 表示该域名未放行；没有 DOI 的行写 UNVERIFIED。Crossref 查不到时（如 arXiv 等 DataCite 登记的 DOI）改查 OpenAlex，中间多一段"OpenAlex · 题目一致 · …"。出版商常对脚本返回 403，只想核验元数据时加 `--no-landing`。

The verified column reads "Crossref result；landing-page result" (落地页 = landing page). "Crossref HTTP 200 · 题目一致" (title matches) means the DOI is valid and points to the paper in the table; 题目不一致 means the titles differ; BLOCKED means that domain is not allowed; rows without a DOI read UNVERIFIED. When Crossref has no record (for example arXiv and other DOIs registered with DataCite), the script checks OpenAlex instead and adds an "OpenAlex · 题目一致 · …" part. Publishers often answer scripts with 403; to check metadata only, add `--no-landing`. With `--lang en` the column is written in English ("title matches", "Landing page").

**可选：以 JSON 为数据源**。把 Markdown 导入为 `evidence/evidence_table.json`（表外文字原样保留，导入时检查能否逐字还原），之后核验写进 JSON 的结构化结果，Markdown 由 JSON 重新生成；Markdown 在上次导入或生成之后被手工改过时，脚本不会覆盖它，会提示先重新导入。

**Optional: JSON as the source of truth.** Import the Markdown into `evidence/evidence_table.json` (text outside the table is kept as is, and the import checks that the file can be regenerated byte for byte). From then on, verification stores structured results in the JSON and the Markdown is regenerated from it; if the Markdown was edited by hand since the last import or render, the scripts leave it alone and ask you to re-import first.

```bash
python3 scripts/logrun.py "T5 证据表转 JSON" -- python3 scripts/evidence.py import-md evidence/evidence_table.md
```

```bash
python3 scripts/logrun.py "T5 DOI 核验" -- python3 scripts/verify.py --table evidence/evidence_table.json
```

```bash
python3 scripts/evidence.py render evidence/evidence_table.json --lang en --out evidence/evidence_table.en.md
```

### T5b 引文追踪（可选）｜ T5b Citation chasing (optional)

关键词检索找不到措辞不同的文献（教程 v1 漏检参考文献就是这个原因）。以证据表中至少 2 个面为 overlap 的文献为种子，查与它们有引用关系的文献：

Keyword search misses papers that use different wording (that is why the tutorial's v1 missed the reference paper). Using the evidence-table papers with at least two overlapping facets as seeds, look for papers linked to them by citations:

```bash
python3 scripts/logrun.py "T5b 引文追踪" -- python3 scripts/snowball.py --from-evidence evidence/evidence_table.md
```

`--from-evidence` 也接受证据 JSON（`evidence/evidence_table.json`）。

`--from-evidence` also accepts the evidence JSON (`evidence/evidence_table.json`).

两步共被引：先取引用种子、且标题摘要满足你给的词组的文献，再看它们共同引用了什么。词组由你决定；种子与想法只在研究情境面不同时，可以用该面"谁在用"的词：

Two-hop co-citation: take the papers that cite the seeds and match a term group you choose in their title and abstract, then see what they cite in common. The term group is your call; if the seeds differ from your idea only in the context facet, try that facet's "who uses it" terms:

```bash
python3 scripts/logrun.py "T5b 共被引" -- python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --cocite --citer-filter 'scientist*'
```

结果在 `results/merged/chase_C1.csv`（一步）、`chase_C2.csv`（共被引）；`in_search` 列标出已在检索结果中的。结果对词组很敏感（教程中用数据与方法面的词过滤时，排在前面的是 VOSviewer、PRISMA 这类通用文献），建议换几个面各跑一次（`--label C3` 等）。值得纳入的文献由你挑选，再按 T5 的格式加进证据表。

The results are in `results/merged/chase_C1.csv` (one hop) and `chase_C2.csv` (co-citation); the `in_search` column marks works already in the search results. Results depend heavily on the term group (in the tutorial, filtering by the data-and-methods terms put generic references such as VOSviewer and PRISMA on top), so try a few facets (`--label C3`, and so on). You choose which papers to add, then add them to the evidence table in the T5 format.

## 7. T6 差异陈述（AI 助手 + 你）｜ T6 Difference statement (AI assistant + you)

把下面任一版本的提示词粘贴给 AI 助手：

Paste either version of the prompt below into the AI assistant:

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

比较两轮：已知文献（如你已经知道的相关论文）各排第几、截断处的并列、前 10 / 前 20 篇的构成：

Compare two rounds: where known papers (for example relevant papers you already know) rank, ties at the cutoff, and the make-up of the top 10 / top 20:

```bash
python3 scripts/logrun.py "比较 v1 与 v2" -- python3 scripts/compare.py --runs ,_v2 --known 10.1038/s41586-025-09922-y
```

教程中 v1b、v2b 两轮就是用改进后的流程重跑并这样比较的，结果见 `docs/IMPROVEMENT_PLAN.md` 第 12 节。

That is how the tutorial's v1b and v2b rounds were re-run with the improved pipeline and compared; see section 12 of `docs/IMPROVEMENT_PLAN.md`.

**联网的接口检查（可选，建议每轮 T3 之前跑一次）**：6 个请求，确认 OpenAlex、Semantic Scholar、Crossref 的接口行为与脚本的假设一致（如 OpenAlex 不支持通配符、arXiv 的 DOI 由 DataCite 登记）。数据源改了接口时，离线测试发现不了，这里能发现。

**Live interface checks (optional; worth running before each T3)**: 6 requests confirming that OpenAlex, Semantic Scholar and Crossref still behave as the scripts assume (for example, OpenAlex rejects wildcards, and arXiv DOIs are registered with DataCite). The offline tests cannot notice when a data source changes its interface; these checks can.

```bash
NP_LIVE=1 python3 -m unittest tests.test_live_contract -v
```

## 常见问题 ｜ Troubleshooting

| 现象<br>Symptom | 原因<br>Cause | 处理<br>Fix |
|---|---|---|
| `FAILED: network error: Tunnel connection failed: 403`，或 `BLOCKED at <域名>`<br>`FAILED: network error: Tunnel connection failed: 403`, or `BLOCKED at <domain>` | 云环境未放行该域名<br>The cloud environment does not allow that domain | 在 Network access 中放行（见"准备"）<br>Allow it under Network access (see Setup) |
| `HTTP 429: Insufficient budget …`（OpenAlex） | 没带 key，共用的每日额度已用完<br>No key, and the shared daily budget is used up | 设置 OpenAlex key 后重跑<br>Set an OpenAlex key and re-run |
| `HTTP 429: Too Many Requests …`（Semantic Scholar） | 匿名限流池繁忙；有 key 时限额为每秒 1 个请求（所有接口合计），同一 key 被别处同时使用也会触发<br>The anonymous rate-limit pool is busy; with a key the limit is 1 request per second across all endpoints, and other use of the same key also counts | 脚本已节流并自动重试；仍失败时等几分钟后用 `--ids`、`--sources` 补跑，或申请 S2 key，不要同时运行两个访问 S2 的脚本<br>The script throttles and retries automatically; if it still fails, wait a few minutes and re-run with `--ids` / `--sources`, or get an S2 key, and do not run two S2-using scripts at once |
| `INVALID: 未登记的截断词 …`、`不支持括号外的 OR` 等<br>`INVALID: 未登记的截断词 …` (unregistered truncation), `不支持括号外的 OR` (OR outside parentheses), etc. | 检索式写法不符合要求<br>The query does not follow the required format | 按 T2 的格式修改 `queries/queries.json`，再跑 `--dry-run`<br>Fix `queries/queries.json` to the T2 format and run `--dry-run` again |
| `results/raw/ 中同一来源混有不同检索方式的结果`<br>(results from different search methods mixed for one source) | 混有旧脚本或旧想法留下的结果<br>Leftover results from an older script or a previous idea | 按第 1 步清空 `results/raw/`，重跑 T3<br>Clear `results/raw/` as in step 1 and re-run T3 |
| 某条检索式在某个来源命中 0 条<br>A query returns 0 hits from one source | 组合太严<br>The combination is too strict | 可以接受；或让助手放宽这条检索式<br>Acceptable; or ask the assistant to loosen that query |
| verified 列为 `Crossref BLOCKED at data.crosscite.org；OpenAlex · …`<br>The verified column reads `Crossref BLOCKED at data.crosscite.org；OpenAlex · …` | arXiv 等 DataCite 登记的 DOI，已改用 OpenAlex 核验<br>A DOI registered with DataCite, such as an arXiv DOI; checked via OpenAlex instead | OpenAlex 一段为"题目一致"即可；也可放行 `data.crosscite.org`<br>Fine if the OpenAlex part says 题目一致 (title matches); or allow `data.crosscite.org` |
| `OpenAlex 没有把排除组解析为 NOT`<br>(OpenAlex did not parse the exclusion as NOT) | NOT 没有大写，或写在了不支持的位置<br>NOT was not upper case, or was placed where it is not supported | 写成 `… AND NOT ("a" OR "b")`，放在最后<br>Write `… AND NOT ("a" OR "b")` at the end |
| `运算符必须大写`、`不支持用 - 表示排除`<br>(operators must be upper case; "-" is not supported for exclusion) | 检索式里有小写的 and / or / not，或以 - 开头的词<br>The query has a lower-case and / or / not, or a word starting with - | 改成大写运算符；排除用 `AND NOT (…)`<br>Use upper-case operators; exclude with `AND NOT (…)` |
| `配置有问题：…`（退出码 2）<br>`Problems in the config: …` (exit code 2) | `novelty-probe.json` 里的取值不合法，所有问题一次列出<br>Invalid values in `novelty-probe.json`; every problem is listed at once | 按提示修改，再跑 `python3 scripts/config.py check`<br>Fix as indicated, then run `python3 scripts/config.py check` |
| `引文不是摘要原文`、`不在检索结果中`（evidence check）<br>`quote is not verbatim`, `not in the retrieval results` (evidence check) | 判定依据里的引文改写了摘要，或 DOI 不是从检索结果里取的<br>A quote paraphrases the abstract, or a DOI did not come from the search results | 从摘要逐字复制；DOI 只取自 `results/` 或 `evidence/enrichment*.json`<br>Copy quotes verbatim from the abstract; take DOIs only from `results/` or `evidence/enrichment*.json` |
| `… 在上次导入或渲染后被手工改过，未覆盖`<br>`… was edited by hand after the last import or render; not overwritten` | 以 JSON 为数据源时手工改了 Markdown<br>The Markdown was edited by hand while the JSON is the source of truth | 先 `python3 scripts/evidence.py import-md <md>` 把改动导入 JSON，再重跑<br>Run `python3 scripts/evidence.py import-md <md>` first, then re-run |

## 目录速查 ｜ Directory reference

| 路径<br>Path | 内容<br>Contents |
|---|---|
| `README.md` | 英文项目介绍<br>Project overview in English |
| `AGENTS.md` | 给 AI 编程助手的说明（中文）<br>Instructions for AI coding assistants (Chinese) |
| `HANDOFF.md` | 交接文档：现状、数据约定、设计决策、已知问题（中文）<br>Handoff notes: status, data contracts, design decisions, known issues (Chinese) |
| `PROJECT.md` | 助手的角色与三条硬规则（中文）<br>The assistant's role and three rules (Chinese) |
| `idea/idea.md` | 你的想法（唯一需要你改的文件）<br>Your idea (the only file you edit) |
| `facets/`、`queries/` | T2 产出<br>T2 outputs |
| `results/raw/`、`results/merged/` | T3、T4 产出<br>T3 and T4 outputs |
| `evidence/` | T5、T6 产出<br>T5 and T6 outputs |
| `logs/RUN_LOG.md` | 运行日志<br>Run log |
| `novelty-probe.json` | 项目配置：只写与默认值不同的设置<br>Project configuration: only the settings that differ from the defaults |
| `docs/IMPROVEMENT_PLAN.md` | 遗留问题的调研、改进计划与评估结果（中文）<br>Research, improvement plan and evaluation for the known issues (Chinese) |
| `docs/ARCHITECTURE_REVIEW.md` | 工具层的架构审视与设计理由（中文）<br>Architecture review and design rationale of the tool layer (Chinese) |
| `docs/ROADMAP.md` | 工具层迭代的总体计划与进度表（中文）<br>Overall plan and progress table of the tool-layer iteration (Chinese) |
| `novelty_probe/` | 各脚本共用的包：HTTP 客户端与缓存、配置、界面语言、证据 JSON<br>Package shared by the scripts: HTTP client and cache, configuration, interface language, evidence JSON |
| `scripts/search.py` | T3 检索（`--dry-run` 检查语法；`--ids`、`--sources` 补跑；`--queries`、`--suffix` 用于新一轮）<br>T3 search (`--dry-run` checks syntax; `--ids`, `--sources` re-run failures; `--queries`, `--suffix` for a new round) |
| `scripts/qa.py` | T3 检索质量检查（`--suffix`）<br>T3 search quality check (`--suffix`) |
| `scripts/merge.py` | T4 合并去重（`--suffix`；`--legacy` 复现 v1、v2 当时的方法）<br>T4 merge and deduplicate (`--suffix`; `--legacy` reproduces the v1/v2 method) |
| `scripts/enrich.py` | T5 从其他版本补摘要（`--top`、`--candidates`、`--out`）<br>T5 abstracts from other versions (`--top`, `--candidates`, `--out`) |
| `scripts/snowball.py` | T5b 引文追踪（`--from-evidence` 或 `--seeds`；`--cocite --citer-filter`；`--suffix`）<br>T5b citation chasing (`--from-evidence` or `--seeds`; `--cocite --citer-filter`; `--suffix`) |
| `scripts/compare.py` | 比较几轮结果（`--runs`、`--known`、`--ignore-phrases`）<br>Compare rounds (`--runs`, `--known`, `--ignore-phrases`) |
| `scripts/textmatch.py` | 共用的文本匹配（词干还原、BM25、版本识别），不单独运行<br>Shared text matching (stemming, BM25, version linking); not run on its own |
| `scripts/authors.py` | T5 查作者（`--top`、`--candidates`、`--out`）<br>T5 author lookup (`--top`, `--candidates`, `--out`) |
| `scripts/verify.py` | T5 DOI 核验（`--table` 可以是 .md 或 .json、`--no-landing`）<br>T5 DOI verification (`--table` may be .md or .json, `--no-landing`) |
| `scripts/evidence.py` | T5 证据表：`check` 检查、`import-md` 转 JSON、`render` 生成 Markdown（`--lang`）<br>T5 evidence table: `check`, `import-md` to JSON, `render` Markdown (`--lang`) |
| `scripts/config.py` | 查看与检查配置（`show`、`show --diff`、`check`、`init`）<br>Show and check the configuration (`show`, `show --diff`, `check`, `init`) |
| `scripts/logrun.py` | 运行一条命令，同时写入 `logs/RUN_LOG.md`<br>Runs a command and records it in `logs/RUN_LOG.md` |
| `tests/` | 离线自检（`python3 -m unittest discover -s tests -v`）；联网接口检查 `NP_LIVE=1 python3 -m unittest tests.test_live_contract -v`<br>Offline self-test; live interface checks with `NP_LIVE=1` |
| `.github/workflows/tests.yml` | GitHub Actions：Python 3.9–3.13 × Ubuntu / Windows / macOS 的离线测试<br>GitHub Actions: offline tests on Python 3.9–3.13 × Ubuntu / Windows / macOS |
