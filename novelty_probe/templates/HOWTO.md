# HOWTO

**用 novelty-probe 为一个研究想法查找文献证据**

**Collecting literature evidence for a research idea with novelty-probe**

> 给研究者的操作指南。工具装一次；每个想法一个项目目录，**你只需要写 `idea/idea.md`**，其余文件由 `novelty-probe` 命令或 AI 编程助手（如 ZCode + GLM、Claude Code）生成。
>
> A guide for researchers. Install the tool once and use one project folder per idea. **The only file you write is `idea/idea.md`.** Everything else is produced by the `novelty-probe` commands or by an AI coding assistant (for example ZCode with GLM, or Claude Code).
>
> 规则见 `PROJECT.md`：不判断新颖性，只找证据；每条文献要有 DOI 或 arXiv ID，否则标 UNVERIFIED；每一步的命令和产出都追加到 `logs/RUN_LOG.md`。
>
> The rules are in `PROJECT.md` (in Chinese): never judge novelty, only collect evidence; every paper needs a DOI or arXiv ID, otherwise it is marked UNVERIFIED; the commands and outputs of every step are appended to `logs/RUN_LOG.md`.

## 流程总览 ｜ Overview

| 步骤<br>Step | 谁来做<br>Done by | 命令或产出<br>Command or output |
|---|---|---|
| 准备：安装、新建项目<br>Setup: install, create a project | 你<br>You | `novelty-probe init <目录 folder>`（第 0–1 节 sections 0–1） |
| T1 写想法<br>Write the idea | 你<br>You | `idea/idea.md` |
| T2 拆面与检索式<br>Facets and queries | AI 助手<br>AI assistant | `facets/facets.md`、`queries/queries.json` |
| T3–T5 脚本步骤：检查检索式、检索、质量检查、合并去重、补摘要<br>Scripted steps: check queries, search, quality check, merge, abstracts | 脚本（一条命令）<br>Scripts (one command) | `novelty-probe run` → `results/`、`evidence/enrichment.json` |
| T5 证据表与核验<br>Evidence table and verification | AI 助手 + 脚本<br>AI assistant + scripts | `evidence/evidence_table.md` |
| T5b 引文追踪（可选）<br>Citation chasing (optional) | 脚本 + 你<br>Script + you | `results/merged/chase_*.csv` |
| T6 差异陈述<br>Difference statement | AI 助手 + 你<br>AI assistant + you | `evidence/difference_statement.md` |

- 命令都在项目目录里运行（或加 `--root <目录>`）。安装后各系统的命令相同：macOS / Linux 的终端、Windows 的 PowerShell 都一样；只有设置环境变量的写法不同，下面分别给出。

  Run every command inside the project folder (or add `--root <folder>`). Once installed, the commands are the same on every system, in a macOS / Linux terminal or in Windows PowerShell; only setting environment variables differs, and both forms are given below.

- **AI 助手步骤**：在项目目录里启动你的 AI 编程助手，先让它读 `AGENTS.md`，再把对应的提示词原样粘贴进去（每个提示词都有中文和英文两个版本，任选其一）。也可以手工完成，按提示词里的格式写文件。

  **AI assistant steps**: start your AI coding assistant in the project folder, have it read `AGENTS.md` first, then paste the corresponding prompt as is (each prompt comes in a Chinese and an English version; use either). You can also do these steps by hand, writing the files in the format the prompt describes.

- **脚本步骤**：`novelty-probe run` 一次跑完，每一步自动写进 `logs/RUN_LOG.md`。单独运行某一步时，在命令后加 `--log "<步骤名>"`，命令与输出同样写进日志，Step 编号自动接着日志里的最后一个。

  **Script steps**: `novelty-probe run` does them all, and every step is appended to `logs/RUN_LOG.md`. To run a single step, add `--log "<step name>"` to the command; the command and its output go into the log the same way, numbered after the last Step in the log.

## 0. 安装（只做一次）｜ Install (one-time)

**Python 3.9 或更高**。novelty-probe 只用标准库，没有其他依赖。

**Python 3.9 or later.** novelty-probe uses only the standard library and has no other dependencies.

```bash
python3 -m pip install "https://github.com/PadSama/novelty-probe-demo/archive/refs/tags/v2.0.0.zip"
```

Windows 上把 `python3` 换成 `py -3`。提示 `externally-managed-environment`（部分 Linux 与 Homebrew 的 Python 不允许直接装包）时，改用 `pipx install "<同一个地址>"`，或先建一个虚拟环境再安装。装好后检查：

On Windows, replace `python3` with `py -3`. If pip reports `externally-managed-environment` (some Linux and Homebrew Pythons do not allow installing packages directly), use `pipx install "<the same address>"` instead, or install into a virtual environment. Then check:

```bash
novelty-probe --version
```

**不安装也可以**：下载或克隆工具仓库后，在其他目录里用 `python3 <工具仓库>/scripts/<命令>.py …`，在工具仓库目录里用 `python3 -m novelty_probe <命令> …`，与 `novelty-probe <命令> …` 等价。

**Without installing**: after downloading or cloning the tool repository, run `python3 <tool repository>/scripts/<command>.py …` from any other folder, or `python3 -m novelty_probe <command> …` inside the tool repository; both are equivalent to `novelty-probe <command> …`.

**API key**（不要写进任何文件，也不要提交到仓库）：

**API keys** (never write them into any file or commit them to a repository):

- **OpenAlex：强烈建议申请**免费 key：https://help.openalex.org/api/authentication/ 。不带 key 时，与同一出口 IP 的所有人共用每日免费额度，云环境里常常已经用完（返回 429 "Insufficient budget"）。在自己电脑上用环境变量设置；云环境里加在 Network secrets 中，不需要环境变量。

  **OpenAlex: strongly recommended.** Get a free key at https://help.openalex.org/api/authentication/ . Without a key, you share a daily free budget with everyone on the same outgoing IP address, and in cloud environments it is often already used up (HTTP 429 "Insufficient budget"). On your own computer, set it as an environment variable; in a cloud environment, add it under Network secrets instead.

- **Semantic Scholar：可选**，申请地址 https://www.semanticscholar.org/product/api#api-key-form 。不带 key 时共用匿名限流池，偶尔返回 429。有 key 时的限额是每秒 1 个请求、所有接口合计，脚本对每个发往 S2 的请求（含翻页与重试）自动节流。脚本会自动重试，仍失败的可以单独补跑（见第 4 节）。

  **Semantic Scholar: optional.** Apply at https://www.semanticscholar.org/product/api#api-key-form . Without a key, you share an anonymous rate-limit pool and occasionally get HTTP 429. With a key, the limit is 1 request per second across all endpoints, and the script throttles every Semantic Scholar request (including pages and retries) accordingly. The script retries automatically; anything that still fails can be re-run on its own (see section 4).

macOS / Linux（写进 `~/.zshrc` 或 `~/.bashrc` 即长期有效）：

macOS / Linux (put the lines in `~/.zshrc` or `~/.bashrc` to keep them):

```bash
export OPENALEX_API_KEY="你的 key / your key"
export S2_API_KEY="你的 key / your key"
```

Windows PowerShell（只对当前窗口有效；长期有效用 `setx OPENALEX_API_KEY "…"`，之后新开的窗口生效）：

Windows PowerShell (for the current window only; to keep it, use `setx OPENALEX_API_KEY "…"`, which applies to windows opened afterwards):

```powershell
$env:OPENALEX_API_KEY = "你的 key / your key"
$env:S2_API_KEY = "你的 key / your key"
```

**网络**：需要能访问下列域名。在自己电脑上运行通常不用处理；在云端沙箱环境（如 Claude Code 的云环境）中运行，要在环境设置的 Network access 里放行。

**Network**: the domains below must be reachable. On your own computer this usually needs no action; in a cloud sandbox (such as a Claude Code cloud environment), allow them under Network access in the environment settings.

| 域名<br>Domain | 用于<br>Used for |
|---|---|
| `api.openalex.org` | 检索、补摘要、引文追踪、补查作者（缺作者时）<br>Search, abstracts from other versions, citation chasing, missing authors |
| `api.semanticscholar.org` | 检索<br>Search |
| `doi.org`、`api.crossref.org` | DOI 核验<br>DOI verification |
| `data.crosscite.org`（可选 optional） | 核验 arXiv 等 DataCite 登记的 DOI<br>Verifying DOIs registered with DataCite, such as arXiv DOIs |
| 各出版商域名（可选）<br>Publisher domains (optional) | 核验落地页标题；不放行时显示 BLOCKED，不影响 Crossref 核验<br>Checking landing-page titles; without access the result reads BLOCKED, which does not affect the Crossref check |

**界面语言**：帮助、报错、verified 列与运行日志默认中文；加 `--lang en`、设环境变量 `NP_LANG=en`（PowerShell：`$env:NP_LANG = "en"`），或在配置里写 `"language": "en"`，即改为英文。

**Interface language**: help, error messages, the verified column and the run log are in Chinese by default; add `--lang en`, set the environment variable `NP_LANG=en` (PowerShell: `$env:NP_LANG = "en"`), or put `"language": "en"` in the configuration to switch to English.

## 1. 新建项目 ｜ Create a project

每个想法一个项目目录。研究想法与检索结果都留在这个目录里，由你自己保管；目录要放在工具仓库之外（命令会拒绝在工具仓库里新建项目）。用 git 管理这个目录时，建议设为私有仓库。

Use one project folder per idea. Your idea and the search results stay in this folder, under your control; keep it outside the tool repository (the command refuses to create a project inside it). If you keep the folder in git, make the repository private.

**公开项目之前**：`results/`、`evidence/enrichment*.json` 与 `.cache/` 里是从 OpenAlex、Semantic Scholar、Crossref 取得的数据（含摘要）。摘要的版权属于出版方或作者；Semantic Scholar 的 API 许可协议只允许非商业的研究与教育用途，并限制把它的数据转给第三方，公开使用时须注明 Semantic Scholar 并链接回它（检索报告里已写好各来源的署名）。所以公开项目时，只放你自己的文件（想法、拆面、检索式、证据表、差异陈述、运行日志、检索报告），按 `.gitignore` 里的说明不提交第三方数据。运行日志里，你的用户目录记成 `~`，不会写进用户名。

**Before you publish a project**: `results/`, `evidence/enrichment*.json` and `.cache/` hold data from OpenAlex, Semantic Scholar and Crossref, abstracts included. Abstracts remain the copyright of their publishers or authors; the Semantic Scholar API license allows only non-commercial research and educational use, restricts passing its data to third parties, and requires public uses to credit Semantic Scholar and link back to it (the search report already credits each source). So publish only your own files (idea, facets, queries, evidence table, difference statement, run log, search report), and follow the note in `.gitignore` to keep the third-party data out. In the run log, your home folder is written as `~`, so your user name does not appear.

```bash
novelty-probe init my-idea
```

```bash
cd my-idea
```

写入的文件：`PROJECT.md`（规则）、`AGENTS.md`（给 AI 助手的说明）、`HOWTO.md`（本指南）、`idea/idea.md`（想法模板）、`novelty-probe.json`（配置）、`logs/RUN_LOG.md`（运行日志，Step 0 记下这次新建）、`.gitignore`，以及空目录 `facets/`、`queries/`、`results/`、`evidence/`。已有的文件一律不覆盖。

Files written: `PROJECT.md` (rules), `AGENTS.md` (instructions for the AI assistant), `HOWTO.md` (this guide), `idea/idea.md` (idea template), `novelty-probe.json` (configuration), `logs/RUN_LOG.md` (run log; Step 0 records this step), `.gitignore`, and the empty folders `facets/`, `queries/`, `results/` and `evidence/`. Existing files are never overwritten.

**项目目录**：命令从当前目录向上找 `novelty-probe.json` 或 `PROJECT.md`，以它所在的目录为项目目录；也可以用 `--root <目录>` 或环境变量 `NOVELTY_PROBE_ROOT` 指定。找不到时报错，不会把结果写到别处。

**Project folder**: the commands look upwards from the current folder for `novelty-probe.json` or `PROJECT.md` and use that folder as the project folder; you can also name it with `--root <folder>` or the environment variable `NOVELTY_PROBE_ROOT`. If none is found, the command stops with an error rather than writing results elsewhere.

**配置**：`novelty-probe.json` 只写与内置默认值不同的设置。查看全部设置与当前配置的指纹（config_hash，写进每个输出文件）、检查写法：

**Configuration**: `novelty-probe.json` holds only the settings that differ from the built-in defaults. To see every setting and the configuration fingerprint (config_hash, recorded in every output file), or to check the file:

```bash
novelty-probe config show
```

```bash
novelty-probe config check
```

常改的设置：`language`（界面语言）、`queries.purposes.concurrent.year_from`（concurrent 检索式的起始年份）、`queries.truncation`（截断词对应的完整词）、`sources.<来源>.top_n` 与 `enabled`、`merge.top_k`、`facets`（面的名称与中英文标签）、`compare.marker_terms`。列表整体替换；要在默认列表后追加，写 `<键>_extend`，例如 `"versions": {"preprint_doi_prefixes_extend": ["10.xxxx/"]}`。改参数属于研究设计，由你决定。

Settings you are most likely to change: `language` (interface language), `queries.purposes.concurrent.year_from` (start year of concurrent queries), `queries.truncation` (full words for truncated terms), `sources.<source>.top_n` and `enabled`, `merge.top_k`, `facets` (facet names with Chinese and English labels), `compare.marker_terms`. Lists are replaced as a whole; to append to a default list, use `<key>_extend`, for example `"versions": {"preprint_doi_prefixes_extend": ["10.xxxx/"]}`. Changing parameters is a research-design decision, and it is yours.

## 2. T1 写想法（你）｜ T1 Write the idea (you)

用一两句话写清：谁、用什么、可能带来什么结果、打算用什么数据，写进 `idea/idea.md`（删掉模板里的说明）。工具仓库的教程示例用的原文：

In one or two sentences, state who does what with which tool, what outcome you expect, and what data you plan to use, and write it in `idea/idea.md` (delete the template's note). The idea used in the tool repository's worked example:

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
检索式格式（novelty-probe search 只认这种写法）：用 AND 连接若干个括号组，括号内只用 OR；短语加英文双引号；运算符一律大写；不用截断符 *、嵌套括号和逗号。需要排除某些说法时，在最后加 AND NOT ("…" OR "…")。
写完运行 novelty-probe search --dry-run，有 INVALID 就按报错修改。完成后把产出文件追加到 logs/RUN_LOG.md。
```

```text
Read idea/idea.md. Following the rules in PROJECT.md:
1) Break the idea into five facets and write them to facets/facets.md: research question, mechanism, context, data and methods, expected findings;
2) Give each facet 3–5 English search terms, including synonyms and the terms used in adjacent disciplines;
3) Combine them into 6 queries in queries/queries.json with the fields id (Q1–Q6), facets_used, query, and purpose (component / application / method / concurrent).
Query format (the only format novelty-probe search accepts): parenthesized groups joined by AND, with only OR inside each group; phrases in English double quotes; operators in upper case; no truncation (*), nested parentheses or commas. To exclude some phrasings, append AND NOT ("…" OR "…") at the end.
When done, run novelty-probe search --dry-run and fix any INVALID query as the error says. Then append the output files to logs/RUN_LOG.md.
```

助手可能会就范围提问（教程示例里问过"AI 工具"是否只指生成式 AI），由你决定。

The assistant may ask you about scope (in the worked example it asked whether "AI tools" meant generative AI only); those decisions are yours.

检查检索式语法（不联网，不消耗额度）：

Check the query syntax (offline; no API budget used):

```bash
novelty-probe search --dry-run
```

倒数第二行应为 `6/6 queries valid`，最后一行是请求估算（各来源最多发多少请求、OpenAlex 最多花多少额度）。有 INVALID 的，报错里带错误码（如 Q115）和出错位置，下一行用 ^ 标出；把报错发给助手，让它修改 `queries/queries.json`。命令会拒绝以下写法，因为它们会让各数据源检索到不同的内容：未配对的引号、逗号、括号内的词之间缺少 OR、组与组之间缺少 AND、截断符 * 不在词尾。

The second-to-last line should read `6/6 queries valid`; the last line is the request estimate (the most requests each source will receive, and the most OpenAlex credits). An INVALID line carries an error code (such as Q115) and the position, marked with ^ on the next line; give the error to the assistant and have it fix `queries/queries.json`. The command rejects these because they would make the sources search different things: an unbalanced quote, a comma, terms inside parentheses without OR, groups without AND between them, and a * that does not end a word.

## 4. T3–T5 脚本步骤：一条命令 ｜ T3–T5 Scripted steps: one command

```bash
novelty-probe run
```

依次运行六步，每一步的命令与输出都写进 `logs/RUN_LOG.md`：

It runs six steps in order, and the command and output of each go into `logs/RUN_LOG.md`:

| 步骤<br>Step | 做什么<br>What it does | 单独运行<br>On its own |
|---|---|---|
| check | 检查检索式（不联网）<br>Check the queries (offline) | `novelty-probe search --dry-run` |
| search | T3 检索<br>T3 search | `novelty-probe search` |
| qa | 检索质量检查<br>Search quality check | `novelty-probe qa` |
| merge | T4 合并去重；写出候选表、RIS、运行清单与检索报告（第 5 节）<br>T4 merge and deduplicate; candidates, RIS, run manifest, search report (section 5) | `novelty-probe merge` |
| authors | 补查作者：只在有候选缺作者时运行<br>Missing authors: only if some candidates have none | `novelty-probe authors` |
| enrich | 从同一研究的其他版本补摘要与 arXiv ID<br>Abstracts and arXiv IDs from other versions of the same work | `novelty-probe enrich` |

- 出错即停，并打印从出错的一步续跑的命令，例如 `novelty-probe run --from search`；`--to merge` 到合并为止；`--dry-run` 只打印各步的命令，不运行。

  It stops at the first error and prints the command that resumes from that step, for example `novelty-probe run --from search`; `--to merge` stops after the merge; `--dry-run` only prints the command of each step.

- 单独运行某一步时加 `--log "<步骤名>"`，例如 `novelty-probe search --log "T3 检索"`，日志与 `run` 写的相同。

  To run one step on its own, add `--log "<step name>"`, for example `novelty-probe search --log "T3 search"`; the log entry is the same as from `run`.

**检索的细节**：

**About the search**:

- 每条检索式分别查 OpenAlex（标题 + 摘要，按 API 的相关度）和 Semantic Scholar（bulk 检索，标题 + 摘要），各存前 25 条到 `results/raw/`，每条记录带作者。S2 的 bulk 接口不按相关度排序，命令取回全部命中（最多 3000 条）后在本地重排：满足的 AND 组数 → BM25 → 被引次数；没有摘要的记录单独排序并按比例穿插，标题相同的只留一条。

  Each query is run against OpenAlex (titles and abstracts, ranked by the API's relevance score) and Semantic Scholar (bulk search on titles and abstracts); the top 25 records from each, with their authors, are saved to `results/raw/`. S2's bulk endpoint does not rank by relevance, so the command fetches all hits (up to 3,000) and re-ranks them locally: number of AND groups matched, then BM25, then citation count. Records without an abstract are ranked separately and interleaved in proportion, and duplicate titles are kept once.

- 排除组 `AND NOT (…)`：OpenAlex 原样发送（必须大写 NOT，小写会被当成普通词，把排除变成必须包含；命令发现 OpenAlex 没有按 NOT 解析时会报错），S2 译为 `+ -(…)`。

  Exclusion groups `AND NOT (…)` are sent to OpenAlex unchanged (NOT must be upper case: OpenAlex treats a lower-case not as an ordinary word and turns the exclusion into a requirement; the command stops if OpenAlex did not parse the NOT), and translated to `+ -(…)` for S2.

- purpose 为 concurrent 的检索式只取 2023 年起的文献。要改年份，在 `novelty-probe.json` 里写 `"queries": {"purposes": {"concurrent": {"year_from": 2024}}}`。

  Queries with the purpose concurrent only return papers from 2023 onwards. To change the year, put `"queries": {"purposes": {"concurrent": {"year_from": 2024}}}` in `novelty-probe.json`.

- 终端每行是一个"检索式 × 来源"：`total_hits` 是 API 报告的命中数，`saved` 是保存条数，`no_id` 是既无 DOI 也无 arXiv ID 的条数。

  Each line of terminal output is one query × source: `total_hits` is the hit count reported by the API, `saved` is the number of records kept, and `no_id` is the number of records with neither a DOI nor an arXiv ID.

有 FAILED 的行，先按原因处理（见"常见问题"），再只补跑失败的部分，然后从质量检查续跑，例如：

For lines marked FAILED, fix the cause first (see Troubleshooting), re-run only what failed, then resume from the quality check, for example:

```bash
novelty-probe search --ids Q3,Q4 --sources semanticscholar --log "T3 补跑"
```

```bash
novelty-probe run --from qa
```

网络层：所有联网的命令都接受 `--http-mode cache`（先查项目目录里的缓存 `.cache/http`，省额度、少挨限流）与 `--refresh`（忽略缓存）；默认 `live`。OpenAlex 对格式错误的检索式不报错而静默改写（例如未配对的引号），命令逐组核对它返回的解析树：分组与发送的不同就报错、不保存；解析树的结构不认识时只记一条警告。运行开头打印请求估算；OpenAlex 剩余额度不够完成余下的请求时会提前警告。

Network layer: every networked command accepts `--http-mode cache` (check the cache `.cache/http` in the project folder first, saving budget and rate-limit hits) and `--refresh` (ignore the cache); the default is `live`. OpenAlex silently rewrites malformed queries (for example an unbalanced quote) instead of reporting an error, so the command compares the parse tree OpenAlex returns with the query group by group: if the grouping differs it stops without saving, and if the tree's structure is unfamiliar it only records a warning. A run starts by printing the request estimate, and warns early if the remaining OpenAlex credits cannot cover the remaining requests.

**可选数据源 Crossref**（默认关闭）：Crossref 不支持布尔检索，命令把包含组的检索词合成一串发送，取回最多 1000 条，再在本地按整条检索式筛选（没有摘要的记录只看标题）、按与 S2 相同的方式排序，有损之处写在每个输出文件的 `meta.lossy` 里。在教程示例上实测，它的检索面向参考文献匹配：长检索式在前 40 条里没有一条满足检索式，两三个词的简单检索式效果好得多。是否开启由你决定；开启方法是在 `novelty-probe.json` 里写：

**Optional source: Crossref** (off by default). Crossref has no Boolean search, so the command sends the include terms as one bag of words, fetches up to 1,000 records, keeps only those whose title and abstract satisfy the whole query (title alone when there is no abstract), and ranks them the same way as S2; what is lost is listed in `meta.lossy` of each output file. Tested on the worked example, its search behaves like reference matching: none of the top 40 records satisfied the long queries, while short queries of two or three terms work much better. Whether to turn it on is your call; to do so, put this in `novelty-probe.json`:

```json
{"sources": {"crossref": {"enabled": true}}}
```

**检索质量检查**（qa）：每个结果文件中，标题 + 摘要满足原检索式的记录有多少（用 Porter 词干还原近似两个 API 的匹配）。末尾"本地匹配的偏差"各行（每个来源一行）给出服务器已按布尔检索式返回、本地却判为不满足的记录比例，即本地匹配漏判的上限（教程示例 v1b：OpenAlex 1.1%，Semantic Scholar 6.4%）；合并时也写进检索报告。

**Search quality check** (qa): how many records in each result file satisfy the original query in their title and abstract (Porter stemming approximates the APIs' matching). The closing "local matching bias" lines (one per source) give the share of records that the server returned for the Boolean query but local matching judges non-conforming, an upper bound on local false negatives (worked example v1b: OpenAlex 1.1%, Semantic Scholar 6.4%); the merge also writes it into the search report.

## 5. T4 合并去重的结果 ｜ T4 What the merge produces

去重全自动，不需要你核对。按 DOI、arXiv ID 去重（预印本平台的版本 DOI 视为同一篇），再识别同一研究的不同版本：规范化标题相同（去掉 "(Just accepted by …)" 之类的发表状态括注）且通过一组保守的检查（年份相差 ≤3、不是两个不同的正式发表 DOI、不是数据集、不是 "Re:" 之类的来信、两边都有作者时至少有一个共同的名字等）才合并；题目几乎相同（相差个别词，或一个包含在另一个里）的，要有共同的作者才合并。证据不足的保持分开，写进 `review` 字段。每次合并与分开都记规则编号（D1–D5 合并，R1–R8 分开），含义见 `merged.json` 的 `meta.dedupe_rules`。年份取正式发表版本，最早版本记在 `year_first`。输出：

Deduplication is automatic; you do not need to check it. Records are deduplicated by DOI and arXiv ID (versioned DOIs on preprint servers count as one work); then versions of the same work are linked: titles that match after normalization (dropping publication-status notes such as "(Just accepted by …)") are merged only if a set of conservative checks passes (years at most 3 apart, not two different journal DOIs, not a dataset, not a "Re:" letter, at least one shared name when both sides have authors, and so on); nearly identical titles (a few words apart, or one contained in the other) are merged only when the records share authors. Pairs without enough evidence stay separate and are listed in the `review` field. Every merge and every separation carries a rule code (D1–D5 merge, R1–R8 keep apart), explained in `meta.dedupe_rules` of `merged.json`. The year is that of the version of record; the earliest version's year is kept in `year_first`. Outputs:

- `results/merged/merged.json`：去重后的全部文献。每篇带作者（`authors`，最多 20 位；`n_authors` 为总数）、出处 `raw_refs`（可回查原始记录）、`field_source`（每个字段取自哪条原始记录）与 `dedupe_rules`（合并所用的规则）。

  `results/merged/merged.json`: all deduplicated works. Each work carries its authors (`authors`, at most 20; `n_authors` is the total), `raw_refs` (pointing back to its raw records), `field_source` (which raw record each field came from) and `dedupe_rules` (the rules used to merge it).

- `results/merged/candidates.csv`：前 20 篇，按倒数排名融合（RRF：在各"检索式 × 来源"列表中的名次 r，累加 1/(60 + r)）排序，BM25（全部检索词）打破并列；`authors` 列为前 3 位作者（超过 3 位加 et al.，与证据表的写法相同）；`hits`、`n_conform`（本地判断满足几条检索式）只作参考。Excel 可直接打开。

  `results/merged/candidates.csv`: the top 20 works, ranked by reciprocal rank fusion (RRF: for each query × source list in which the work appears at rank r, add 1/(60 + r)), with BM25 over all query terms breaking ties; the `authors` column lists the first 3 authors (with et al. beyond 3, as in the evidence table); `hits` and `n_conform` (how many queries the work satisfies, checked locally) are shown for reference. Opens directly in Excel.

- `results/merged/candidates.ris`：同样 20 篇的 RIS，可导入 Zotero（文件 → 导入）、EndNote（File → Import，格式选 Reference Manager (RIS)）等文献管理软件。每条的备注（N1）记来自哪些检索式与来源。

  `results/merged/candidates.ris`: the same 20 works as RIS, for import into Zotero (File → Import), EndNote (File → Import, format Reference Manager (RIS)) and other reference managers. Each record's note (N1) says which queries and sources it came from.

- `results/merged/run_manifest.json`、`results/merged/search_report.md`：运行清单（每个检索结果文件的检索式、日期、命中数与哈希，配置指纹，产出文件的哈希）与据此生成的检索报告（格式参照 PRISMA-S：数据库与接口、检索式原文与实际发送的写法、各检索式的结果数、去重与候选、本地匹配的偏差）。写论文的检索方法部分时可直接引用。

  `results/merged/run_manifest.json`, `results/merged/search_report.md`: the run manifest (each result file's query, date, hit count and hash; the configuration fingerprint; hashes of the outputs) and the search report generated from it (following PRISMA-S: databases and interfaces, each query as written and as sent, result counts per query, deduplication and candidates, local matching bias). Ready to cite when you write up the search method.

- `evidence/enrichment.json`（补摘要一步）：为没有摘要的候选从同一研究的其他版本（如 arXiv 预印本）补到的摘要与 arXiv ID，连同来源。

  `evidence/enrichment.json` (the abstract step): abstracts and arXiv IDs found for candidates in other versions of the same work (such as the arXiv preprint), with their sources.

注意：排名反映检索式与文本的匹配，不代表与研究问题的相关度。

Note: the ranking reflects how well the text matches the queries, not relevance to your research question.

## 6. T5 证据表与核验（AI 助手 + 脚本）｜ T5 Evidence table and verification (AI assistant + scripts)

作者随检索一起取得，在候选表的 `authors` 列。只有在用旧结果（2026-11 之前检索的，没有作者）或个别记录缺作者时，`run` 才会运行补查作者一步（`novelty-probe authors`）：它先用合并记录里的作者，只为缺作者的候选查 OpenAlex，结果写到 `evidence/authors.json`。

Authors come with the search results (the `authors` column of the candidates table). Only for older results (searched before November 2026, without authors) or when some records lack authors does `run` include the author step (`novelty-probe authors`): it uses the authors in the merged records and queries OpenAlex only for candidates that have none, writing `evidence/authors.json`.

把下面任一版本的提示词粘贴给 AI 助手：

Paste either version of the prompt below into the AI assistant:

```text
读 results/merged/candidates.csv 前 10 篇的摘要（作者取 authors 列；该列为空时见 evidence/authors.json），对照 facets/facets.md，逐面标 overlap / differ / unknown，写到 evidence/evidence_table.md。
表格列：rank, 作者, 年份, 题目, DOI/arXiv, 研究问题, 作用机制, 研究情境, 数据与方法, 预期发现, verified。
DOI/arXiv 列写成 doi:<DOI>，有 arXiv ID 时加上 " · arXiv:<ID>"；verified 列先写"待核验"。
在文件开头写明标注规则，在表下逐篇写判定依据（每篇以 **rank · merged_id** 开头）并引用摘要原文。候选本身没有摘要时，可以用 evidence/enrichment.json 中补到的摘要，并注明来源（DOI）。
写完后运行 novelty-probe evidence check evidence/evidence_table.md，按报告修改，直到没有问题。不判断新颖性；把产出文件追加到 logs/RUN_LOG.md。
```

```text
Read the abstracts of the top 10 works in results/merged/candidates.csv (take the authors from the authors column; if it is empty, see evidence/authors.json). Compare each with facets/facets.md, label every facet overlap / differ / unknown, and write the result to evidence/evidence_table.md.
Table columns: rank, Authors, Year, Title, DOI/arXiv, Research question, Mechanism, Context, Data and methods, Expected findings, verified.
Write the DOI/arXiv column as doi:<DOI>, adding " · arXiv:<ID>" when there is an arXiv ID; put "pending" in the verified column for now.
State the labeling rules at the top of the file, and below the table give the evidence for each paper (each starting with **rank · merged_id**), quoting the abstract. If a candidate has no abstract, you may use the abstract in evidence/enrichment.json, citing its source (DOI).
When done, run novelty-probe evidence check evidence/evidence_table.md and fix what it reports until no problems remain. Do not judge novelty; append the output files to logs/RUN_LOG.md.
```

检查证据表（不联网）：取值是否合法；DOI、arXiv ID 是否来自检索结果（规则 2）；题目、年份、作者是否与检索结果一致；判定依据里引号内的英文是否为摘要原文（大小写、标点不计；"..." 表示省略）。有问题时退出码为 1，并逐条列出：

Check the evidence table (no network): labels are valid; DOIs and arXiv IDs come from the search results (rule 2); titles, years and authors match the search results; quoted English text in the evidence is verbatim from the abstract (case and punctuation ignored; "..." marks an omission). Problems are listed one by one, with exit code 1:

```bash
novelty-probe evidence check evidence/evidence_table.md --log "T5 证据表检查"
```

核验 DOI，结果写回 verified 列：

Verify the DOIs; the results are written back into the verified column:

```bash
novelty-probe verify --log "T5 DOI 核验"
```

verified 列格式为"Crossref 结果；落地页结果"。"Crossref HTTP 200 · 题目一致"表示 DOI 有效，且指向表中这篇；BLOCKED 表示该域名未放行；没有 DOI 的行写 UNVERIFIED。Crossref 查不到时（如 arXiv 等 DataCite 登记的 DOI）改查 OpenAlex，中间多一段"OpenAlex · 题目一致 · …"。出版商常对脚本返回 403，只想核验元数据时加 `--no-landing`。

The verified column reads "Crossref result；landing-page result" (落地页 = landing page). "Crossref HTTP 200 · 题目一致" (title matches) means the DOI is valid and points to the paper in the table; 题目不一致 means the titles differ; BLOCKED means that domain is not allowed; rows without a DOI read UNVERIFIED. When Crossref has no record (for example arXiv and other DOIs registered with DataCite), the command checks OpenAlex instead and adds an "OpenAlex · 题目一致 · …" part. Publishers often answer scripts with 403; to check metadata only, add `--no-landing`. With `--lang en` the column is written in English ("title matches", "Landing page").

**可选：以 JSON 为数据源**。把 Markdown 导入为 `evidence/evidence_table.json`（表外文字原样保留，导入时检查能否逐字还原），之后核验写进 JSON 的结构化结果，Markdown 由 JSON 重新生成；Markdown 在上次导入或生成之后被手工改过时，命令不会覆盖它，会提示先重新导入。

**Optional: JSON as the source of truth.** Import the Markdown into `evidence/evidence_table.json` (text outside the table is kept as is, and the import checks that the file can be regenerated byte for byte). From then on, verification stores structured results in the JSON and the Markdown is regenerated from it; if the Markdown was edited by hand since the last import or render, the commands leave it alone and ask you to re-import first.

```bash
novelty-probe evidence import-md evidence/evidence_table.md --log "T5 证据表转 JSON"
```

```bash
novelty-probe verify --table evidence/evidence_table.json --log "T5 DOI 核验"
```

```bash
novelty-probe evidence render evidence/evidence_table.json --lang en --out evidence/evidence_table.en.md
```

### T5b 引文追踪（可选）｜ T5b Citation chasing (optional)

关键词检索找不到措辞不同的文献（教程示例 v1 漏检参考文献就是这个原因）。以证据表中至少 2 个面为 overlap 的文献为种子，查与它们有引用关系的文献：

Keyword search misses papers that use different wording (that is why the worked example's v1 missed the reference paper). Using the evidence-table papers with at least two overlapping facets as seeds, look for papers linked to them by citations:

```bash
novelty-probe snowball --from-evidence evidence/evidence_table.md --log "T5b 引文追踪"
```

`--from-evidence` 也接受证据 JSON（`evidence/evidence_table.json`）。

`--from-evidence` also accepts the evidence JSON (`evidence/evidence_table.json`).

两步共被引：先取引用种子、且标题摘要满足你给的词组的文献，再看它们共同引用了什么。词组由你决定；种子与想法只在研究情境面不同时，可以用该面"谁在用"的词：

Two-hop co-citation: take the papers that cite the seeds and match a term group you choose in their title and abstract, then see what they cite in common. The term group is your call; if the seeds differ from your idea only in the context facet, try that facet's "who uses it" terms:

```bash
novelty-probe snowball --from-evidence evidence/evidence_table.md --cocite --citer-filter "scientist*" --log "T5b 共被引"
```

结果在 `results/merged/chase_C1.csv`（一步）、`chase_C2.csv`（共被引）；`in_search` 列标出已在检索结果中的。结果对词组很敏感（教程示例中用数据与方法面的词过滤时，排在前面的是 VOSviewer、PRISMA 这类通用文献），建议换几个面各跑一次（`--label C3` 等）。值得纳入的文献由你挑选，再按 T5 的格式加进证据表。

The results are in `results/merged/chase_C1.csv` (one hop) and `chase_C2.csv` (co-citation); the `in_search` column marks works already in the search results. Results depend heavily on the term group (in the worked example, filtering by the data-and-methods terms put generic references such as VOSviewer and PRISMA on top), so try a few facets (`--label C3`, and so on). You choose which papers to add, then add them to the evidence table in the T5 format.

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

想法另存为新文件，所有产出加版本后缀，不覆盖上一轮。

Save the idea as a new file and give every output a version suffix, so the previous round is not overwritten.

修改 `idea/idea_v2.md`（`idea/idea.md` 的副本），再用 T2 的提示词让 AI 助手生成 `facets/facets_v2.md` 和 `queries/queries_v2.json`（把提示词里的文件名都换成 `_v2` 版本）。然后：

Edit `idea/idea_v2.md` (a copy of `idea/idea.md`), then use the T2 prompt to have the assistant produce `facets/facets_v2.md` and `queries/queries_v2.json` (change every file name in the prompt to its `_v2` version). Then:

```bash
novelty-probe run --suffix _v2
```

检索式文件默认取 `queries/queries_v2.json`（`--queries` 可另指定）；结果写到 `results/raw/*_v2.json`、`results/merged/candidates_v2.csv` 等。用 T5 的提示词让 AI 助手把证据表写到 `evidence/evidence_table_v2.md`（输入换成 `candidates_v2.csv`、`facets_v2.md`），然后：

The query file defaults to `queries/queries_v2.json` (`--queries` names another); results go to `results/raw/*_v2.json`, `results/merged/candidates_v2.csv` and so on. Use the T5 prompt to have the assistant write the evidence table to `evidence/evidence_table_v2.md` (with `candidates_v2.csv` and `facets_v2.md` as inputs), then:

```bash
novelty-probe verify --table evidence/evidence_table_v2.md --log "T5 v2 DOI 核验"
```

比较两轮：已知文献（如你已经知道的相关论文）各排第几、截断处的并列、前 10 / 前 20 篇的构成：

Compare two rounds: where known papers (for example relevant papers you already know) rank, ties at the cutoff, and the make-up of the top 10 / top 20:

```bash
novelty-probe compare --runs ",_v2" --known 10.1038/s41586-025-09922-y --log "比较 v1 与 v2"
```

## 9. 导出与报告（可选）｜ Export and report (optional)

合并时已经写出候选的 RIS 与检索报告；其他范围的 RIS、换语言的报告、比较两次运行（都不联网）：

The merge already writes the candidates' RIS and the search report. For RIS of other selections, the report in another language, or a comparison of two runs (none of these use the network):

```bash
novelty-probe export --all
```

```bash
novelty-probe export --evidence evidence/evidence_table.md
```

```bash
novelty-probe report render results/merged/run_manifest.json --lang en --out results/merged/search_report.en.md
```

```bash
novelty-probe report diff results/merged/run_manifest.json results/merged/run_manifest_v2.json
```

`--all` 导出全部合并记录（`merged.ris`）；`--evidence` 导出证据表各行，各面的标注写成关键词（KW）；`diff` 列出两次运行间检索结果的变化（命中数、保存数、哈希）与候选的进出。

`--all` exports all merged works (`merged.ris`); `--evidence` exports the evidence-table rows with each facet's label as a keyword (KW); `diff` lists what changed between two runs: search results (hit counts, records saved, hashes) and candidates added or dropped.

## 10. 升级工具 ｜ Upgrading

用第 0 节的命令装新版本（地址里换成新的版本号），再在每个项目目录里刷新三份文档（`PROJECT.md`、`AGENTS.md`、`HOWTO.md`；你写的文件不会被改动，刷新记进运行日志）：

Install the new version with the command from section 0 (with the new version number in the address), then refresh the three documents in each project folder (`PROJECT.md`, `AGENTS.md`, `HOWTO.md`; your own files are not touched, and the refresh is logged):

```bash
novelty-probe init . --update-docs
```

## 常见问题 ｜ Troubleshooting

| 现象<br>Symptom | 原因<br>Cause | 处理<br>Fix |
|---|---|---|
| `novelty-probe: command not found`，或 PowerShell 提示无法识别<br>`novelty-probe: command not found`, or PowerShell does not recognize it | 安装位置不在 PATH 中（如 `pip install --user` 装到 `~/.local/bin`）<br>The install location is not on PATH (for example `pip install --user` puts it in `~/.local/bin`) | 把 pip 提示的目录加进 PATH，或用 pipx 安装；临时可用 `python3 -m novelty_probe`<br>Add the folder pip names to PATH, or install with pipx; meanwhile `python3 -m novelty_probe` works |
| `externally-managed-environment`（pip） | 系统的 Python 不允许直接装包<br>The system Python does not allow installing packages | 改用 `pipx install "<地址>"`，或在虚拟环境中安装<br>Use `pipx install "<address>"`, or install into a virtual environment |
| `找不到项目目录` / `No project folder found` | 当前目录及其上级都不是项目目录<br>Neither the current folder nor any parent is a project folder | 先 `cd` 进项目目录，或加 `--root <目录>`；还没有项目时用 `novelty-probe init`<br>`cd` into the project folder or add `--root <folder>`; to start one, use `novelty-probe init` |
| `FAILED: network error: Tunnel connection failed: 403`，或 `BLOCKED at <域名>`<br>`FAILED: network error: Tunnel connection failed: 403`, or `BLOCKED at <domain>` | 云环境未放行该域名<br>The cloud environment does not allow that domain | 在 Network access 中放行（见第 0 节）<br>Allow it under Network access (see section 0) |
| `HTTP 429: Insufficient budget …`（OpenAlex） | 没带 key，共用的每日额度已用完<br>No key, and the shared daily budget is used up | 设置 OpenAlex key 后重跑<br>Set an OpenAlex key and re-run |
| `HTTP 429: Too Many Requests …`（Semantic Scholar） | 匿名限流池繁忙；有 key 时限额为每秒 1 个请求（所有接口合计），同一 key 被别处同时使用也会触发<br>The anonymous rate-limit pool is busy; with a key the limit is 1 request per second across all endpoints, and other use of the same key also counts | 命令已节流并自动重试；仍失败时等几分钟后用 `--ids`、`--sources` 补跑，或申请 S2 key，不要同时运行两个访问 S2 的命令<br>The command throttles and retries automatically; if it still fails, wait a few minutes and re-run with `--ids` / `--sources`, or get an S2 key, and do not run two S2-using commands at once |
| `INVALID: …（Q1xx，第 N 个字符）`<br>`INVALID: … (Q1xx, at character N)` | 检索式写法不合要求，错误码与位置见报错，^ 标出位置<br>The query breaks a format rule; the code and position are in the message, marked with ^ | 按报错修改；常见的是括号内漏写 OR、组之间漏写 AND、引号不配对<br>Fix as indicated; common causes are a missing OR inside parentheses, a missing AND between groups, or an unbalanced quote |
| `INVALID: 未登记的截断词 …`<br>`INVALID: …` (unregistered truncation) | 用了配置 `queries.truncation` 里没有的截断词<br>A truncated term not listed in `queries.truncation` | 换成完整的词，或在配置里登记<br>Use the full words, or register the term in the configuration |
| `运算符必须大写`、`不支持用 - 表示排除`<br>(operators must be upper case; "-" is not supported for exclusion) | 检索式里有小写的 and / or / not，或以 - 开头的词<br>The query has a lower-case and / or / not, or a word starting with - | 改成大写运算符；排除用 `AND NOT (…)`<br>Use upper-case operators; exclude with `AND NOT (…)` |
| `OpenAlex 对检索式的分组与发送的不同`<br>(OpenAlex grouped the query differently) | OpenAlex 改写了检索式的含义（如把一个 OR 组拆开）<br>OpenAlex changed the meaning of the query (for example by splitting an OR group) | 按报错里的两种分组对照修改检索式；带连字符的词加引号<br>Compare the two groupings in the message and fix the query; quote hyphenated terms |
| `OpenAlex 没有把排除组解析为 NOT`<br>(OpenAlex did not parse the exclusion as NOT) | NOT 没有大写，或写在了不支持的位置<br>NOT was not upper case, or was placed where it is not supported | 写成 `… AND NOT ("a" OR "b")`，放在最后<br>Write `… AND NOT ("a" OR "b")` at the end |
| `results/raw/ 中同一来源混有不同检索方式的结果`<br>(results from different search methods mixed for one source) | 混有旧版本工具或上一个想法留下的结果<br>Leftover results from an older tool version or a previous idea | 新想法用新的项目目录；同一想法换版本后缀重跑<br>Use a new project folder for a new idea; for the same idea, re-run with a version suffix |
| 某条检索式在某个来源命中 0 条<br>A query returns 0 hits from one source | 组合太严<br>The combination is too strict | 可以接受；或让助手放宽这条检索式<br>Acceptable; or ask the assistant to loosen that query |
| 候选表的 `authors` 列为空<br>The `authors` column of the candidates table is empty | 结果是 2026-11 之前检索的（当时不取作者），或该数据源没有给出作者<br>The results were searched before November 2026 (when authors were not fetched), or the source gave no authors | `novelty-probe run --from authors`，或重跑检索<br>`novelty-probe run --from authors`, or re-run the search |
| verified 列为 `Crossref BLOCKED at data.crosscite.org；OpenAlex · …`<br>The verified column reads `Crossref BLOCKED at data.crosscite.org；OpenAlex · …` | arXiv 等 DataCite 登记的 DOI，已改用 OpenAlex 核验<br>A DOI registered with DataCite, such as an arXiv DOI; checked via OpenAlex instead | OpenAlex 一段为"题目一致"即可；也可放行 `data.crosscite.org`<br>Fine if the OpenAlex part says 题目一致 (title matches); or allow `data.crosscite.org` |
| `配置有问题：…`（退出码 2）<br>`Problems in the config: …` (exit code 2) | `novelty-probe.json` 里的取值不合法，所有问题一次列出<br>Invalid values in `novelty-probe.json`; every problem is listed at once | 按提示修改，再跑 `novelty-probe config check`<br>Fix as indicated, then run `novelty-probe config check` |
| `引文不是摘要原文`、`不在检索结果中`（evidence check）<br>`quote is not verbatim`, `not in the retrieval results` (evidence check) | 判定依据里的引文改写了摘要，或 DOI 不是从检索结果里取的<br>A quote paraphrases the abstract, or a DOI did not come from the search results | 从摘要逐字复制；DOI 只取自 `results/` 或 `evidence/enrichment*.json`<br>Copy quotes verbatim from the abstract; take DOIs only from `results/` or `evidence/enrichment*.json` |
| `… 在上次导入或渲染后被手工改过，未覆盖`<br>`… was edited by hand after the last import or render; not overwritten` | 以 JSON 为数据源时手工改了 Markdown<br>The Markdown was edited by hand while the JSON is the source of truth | 先 `novelty-probe evidence import-md <md>` 把改动导入 JSON，再重跑<br>Run `novelty-probe evidence import-md <md>` first, then re-run |

**联网的接口检查**（在工具仓库里运行，建议每轮检索之前跑一次）：6 个请求，确认 OpenAlex、Semantic Scholar、Crossref 的接口行为与命令的假设一致（如 OpenAlex 不支持通配符、arXiv 的 DOI 由 DataCite 登记）。数据源改了接口时，离线测试发现不了，这里能发现。

**Live interface checks** (run inside the tool repository; worth running before each round of searching): 6 requests confirming that OpenAlex, Semantic Scholar and Crossref still behave as the commands assume (for example, OpenAlex rejects wildcards, and arXiv DOIs are registered with DataCite). The offline tests cannot notice when a data source changes its interface; these checks can.

```bash
NP_LIVE=1 python3 -m unittest tests.test_live_contract -v
```

```powershell
$env:NP_LIVE = "1"; py -3 -m unittest tests.test_live_contract -v
```

## 命令速查 ｜ Command reference

每个命令的全部参数：`novelty-probe <命令> --help`。所有命令都接受 `--root`、`--config`、`--lang zh|en`；单独运行时加 `--log "<步骤名>"` 写进运行日志。

All options of a command: `novelty-probe <command> --help`. Every command accepts `--root`, `--config` and `--lang zh|en`; add `--log "<step name>"` to record a single run in the run log.

| 命令<br>Command | 作用<br>Purpose |
|---|---|
| `novelty-probe init [目录]` | 新建项目目录（`--update-docs` 只刷新三份文档）<br>Create a project folder (`--update-docs` refreshes only the three documents) |
| `novelty-probe run` | 一条命令跑完脚本步骤（`--from`、`--to`、`--suffix`、`--dry-run`）<br>Run the scripted steps (`--from`, `--to`, `--suffix`, `--dry-run`) |
| `novelty-probe search` | T3 检索（`--dry-run` 检查语法；`--ids`、`--sources` 补跑；`--queries`、`--suffix` 用于新一轮）<br>T3 search (`--dry-run` checks syntax; `--ids`, `--sources` re-run failures; `--queries`, `--suffix` for a new round) |
| `novelty-probe qa` | 检索质量检查（`--suffix`）<br>Search quality check (`--suffix`) |
| `novelty-probe merge` | T4 合并去重，写出候选表、RIS、运行清单与检索报告（`--suffix`；`--legacy` 复现教程 v1、v2 当时的方法）<br>T4 merge and deduplicate, writing candidates, RIS, run manifest and search report (`--suffix`; `--legacy` reproduces the tutorial's v1/v2 method) |
| `novelty-probe authors` | 补查作者：只查缺作者的候选（`--top`、`--candidates`、`--out`）<br>Missing authors, only for candidates that have none (`--top`, `--candidates`, `--out`) |
| `novelty-probe enrich` | 从其他版本补摘要（`--top`、`--candidates`、`--out`）<br>Abstracts from other versions (`--top`, `--candidates`, `--out`) |
| `novelty-probe evidence` | 证据表：`check` 检查、`import-md` 转 JSON、`render` 生成 Markdown<br>Evidence table: `check`, `import-md` to JSON, `render` Markdown |
| `novelty-probe verify` | DOI 核验（`--table` 可以是 .md 或 .json、`--no-landing`）<br>DOI verification (`--table` may be .md or .json, `--no-landing`) |
| `novelty-probe snowball` | T5b 引文追踪（`--from-evidence` 或 `--seeds`；`--cocite --citer-filter`；`--suffix`）<br>T5b citation chasing (`--from-evidence` or `--seeds`; `--cocite --citer-filter`; `--suffix`) |
| `novelty-probe compare` | 比较几轮结果（`--runs`、`--known`、`--ignore-phrases`）<br>Compare rounds (`--runs`, `--known`, `--ignore-phrases`) |
| `novelty-probe export` | 导出 RIS（`--all` 全部合并记录、`--evidence` 证据表各行）<br>Export RIS (`--all` all merged works, `--evidence` evidence-table rows) |
| `novelty-probe report` | 检索报告：`render` 按清单重新生成（`--lang`）、`diff` 比较两次运行<br>Search report: `render` from a manifest (`--lang`), `diff` two runs |
| `novelty-probe config` | 查看与检查配置（`show`、`show --diff`、`check`、`init`）<br>Show and check the configuration (`show`, `show --diff`, `check`, `init`) |
| `novelty-probe logrun "<步骤名>" -- <命令>` | 运行任意命令，并把命令与输出写进运行日志<br>Run any command and record it with its output in the run log |

## 项目目录速查 ｜ Project folder reference

| 路径<br>Path | 内容<br>Contents |
|---|---|
| `PROJECT.md` | 助手的角色与三条硬规则（中文）<br>The assistant's role and three rules (Chinese) |
| `AGENTS.md` | 给 AI 编程助手的说明（中文）<br>Instructions for AI coding assistants (Chinese) |
| `HOWTO.md` | 本指南<br>This guide |
| `novelty-probe.json` | 项目配置：只写与默认值不同的设置<br>Project configuration: only the settings that differ from the defaults |
| `idea/idea.md` | 你的想法（唯一需要你写的文件）<br>Your idea (the only file you write) |
| `facets/`、`queries/` | T2 产出<br>T2 outputs |
| `results/raw/` | 检索的原始结果；`chase_*` 为引文追踪结果<br>Raw search results; `chase_*` are citation-chasing results |
| `results/merged/` | 合并结果、候选表与 RIS、运行清单与检索报告、引文追踪与比较的结果<br>Merged results, candidates (CSV and RIS), run manifests and search reports, chase lists and comparisons |
| `evidence/` | 证据表、补到的摘要、补查的作者、差异陈述<br>Evidence tables, abstracts from other versions, looked-up authors, difference statement |
| `logs/RUN_LOG.md` | 运行日志（只追加）<br>Run log (append only) |
| `.cache/http` | HTTP 缓存（可以删除；`.gitignore` 已忽略）<br>HTTP cache (safe to delete; ignored by `.gitignore`) |
