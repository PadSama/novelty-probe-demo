# 交接文档：novelty-probe 本地移植

> **写给**：在本地用 ZCode + GLM 5.3 接手本项目的研究者本人，以及 ZCode 里的 AI 助手。
>
> **范围**：项目现状、本地环境准备、在 ZCode 里的用法、数据格式约定、脚本速查、已定的设计决策、已知问题、Git 与发布流程、检查清单。操作步骤见 `HOWTO.md`，AI 助手的行为规则见 `AGENTS.md` 与 `PROJECT.md`。

## 1. 项目是什么

一个围绕研究想法检索文献证据的流程：

1. 把想法拆成五个面（研究问题、作用机制、研究情境、数据与方法、预期发现）；
2. 组合布尔检索式，检索 OpenAlex 和 Semantic Scholar；
3. 合并去重，对前 10 篇候选逐面标注 overlap / differ / unknown；
4. 用 Crossref 核验每个 DOI。

流程**不判断新颖性**，只整理可核验的证据，由研究者判断。

## 2. 当前状态

| 项目 | 状态 |
|---|---|
| 仓库 | https://github.com/PadSama/novelty-probe-demo （公开，MIT 许可证） |
| 发布 | v1.0.0（标签打在 3f00b7a） |
| v1.0.0 之后的改动 | CITATION.cff 加入 ORCID、标题大小写修正；本次交接新增 `AGENTS.md`、`HANDOFF.md`、`tests/`、`.gitignore`，以及脚本的几处健壮性修改 |
| 默认分支 | `main`，受规则集保护：禁止删除、禁止强推、必须通过 PR 合并（审批人数 0） |
| 引用信息 | `CITATION.cff`：作者 Yuan, Quan；ORCID 0009-0009-3011-3739；version 1.0.0 |
| 示例运行 | v1（未限定学科）与 v2（管理学与经济学）两轮的全部产出都在仓库里；全过程见 `logs/RUN_LOG.md` Step 0–23 |

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
| `S2_API_KEY` | 可选 | https://www.semanticscholar.org/product/api#api-key-form |

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

- **需要访问的域名**：在自己电脑上通常不用设置。需要能访问 `api.openalex.org`、`api.semanticscholar.org`、`doi.org`、`api.crossref.org`；`data.crosscite.org` 和出版商网站可选。
- **需要代理的网络**：设置 `HTTPS_PROXY`。脚本用 Python 标准库 `urllib`，会自动读取这个变量。
- **macOS 证书问题**：用 python.org 安装包装的 Python，可能报 `CERTIFICATE_VERIFY_FAILED`。运行 `/Applications/Python 3.x/Install Certificates.command` 即可。

### 3.5 离线自检（必做）

```bash
python3 -m unittest discover -s tests -v
```

应显示 `Ran 21 tests … OK`，用时几秒，不联网，也不改动仓库文件。其中一项会用仓库里已提交的原始结果重跑合并，再和已提交的合并结果逐字节比较。全部通过，说明本机的 Python 和脚本逻辑与原环境一致。

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

3. 需要助手完成的步骤是：T2（拆面与检索式）、T5（证据表标注）、T6 第 1 节（选出最接近的三篇）。提示词在 `HOWTO.md` 第 3、6、7 节，中英文任选。
4. 脚本步骤可以让助手执行，也可以自己在终端执行，命令一律用 `logrun.py` 包起来。
5. 每一步结束后检查三件事：命令和产出是否写进了 RUN_LOG；DOI、作者是否都来自检索结果；有没有出现新颖性结论。

**换用 GLM 后要特别留意的地方**（都来自本项目实际遇到过的问题，前三条已由 `search.py` 自动检查，第四条由 `verify.py` 检查）：

- 助手可能把 JSON 包在 Markdown 代码块里写进 `queries.json`，`search.py` 会报"不是合法的 JSON"；
- `id` 必须是 Q1–Q6 这样的格式，`purpose` 必须是四个取值之一；
- 检索式里不能有截断符 `*`、NOT 和逗号；
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
results/raw/{来源}_{Qn}{后缀}.json        每条检索式 × 每个来源，前 25 条
  │  T4 scripts/merge.py
  ▼
results/merged/merged{后缀}.json + candidates{后缀}.csv（前 20 篇）
  │  T5 scripts/authors.py ──► OpenAlex /works/doi:
  ▼
evidence/authors.json ──► AI 助手标注 ──► evidence/evidence_table.md
  │  T5 scripts/verify.py ──► doi.org → Crossref 元数据；doi.org → 出版商落地页
  ▼
verified 列写回证据表
  │  T6 AI 助手 + 研究者
  ▼
evidence/difference_statement.md
```

| 路径 | 作用 | 由谁生成 | 被谁读取 |
|---|---|---|---|
| `idea/idea.md` | 研究想法原文 | 研究者 | T2 |
| `facets/facets.md` | 五个面与检索词 | AI 助手（T2） | 研究者、T5 标注 |
| `queries/queries.json` | 6 条布尔检索式 | AI 助手（T2） | `search.py` |
| `results/raw/*.json` | 原始检索结果 | `search.py` | `merge.py` |
| `results/merged/merged*.json` | 去重后的全部文献 | `merge.py` | 研究者、AI 助手 |
| `results/merged/candidates*.csv` | 前 20 篇候选 | `merge.py` | `authors.py`、T5 标注 |
| `evidence/authors*.json` | 候选的作者 | `authors.py` | T5 标注 |
| `evidence/evidence_table*.md` | 逐面标注与 DOI 核验 | AI 助手 + `verify.py` | 研究者、T6 |
| `evidence/difference_statement.md` | 差异陈述 | AI 助手（第 1 节）+ 研究者（第 2、3 节） | 研究者 |
| `logs/RUN_LOG.md` | 只追加的运行日志 | `logrun.py` + AI 助手 | 所有人 |
| `tests/test_offline.py` | 离线自检 | — | 改代码后运行 |

## 6. 数据格式约定

### 6.1 `queries/queries.json`

JSON 数组，每条形如：

```json
{"id": "Q1", "facets_used": ["mechanism", "context"], "query": "(\"large language models\" OR \"generative AI\") AND (homogenization OR \"collective diversity\")", "purpose": "component"}
```

- **语法**：用 AND 连接若干个括号组，括号内只用 OR；短语加英文双引号；不用 `*`、NOT、嵌套括号和逗号。
- **检查**：`search.py` 的 `load_queries()` 检查 JSON 格式、id 格式与是否重复、query 是否为空、purpose 取值；`--dry-run` 另外检查检索式语法，并打印两个来源实际会发送的检索串。
- **截断词**：只有 `search.py` 中 `TRUNCATION` 表登记过的截断词才能用（如 `bibliometric*`），其他截断词会报错。HOWTO 的提示词要求不用截断，这样最省事。

### 6.2 `results/raw/{source}_{id}{suffix}.json`

```text
{"meta": {...}, "records": [...]}
meta    source_api, query_id, purpose, queries_file, query_original, year_from, conversion, query_sent,
        api_interpretation（仅 OpenAlex）, request_url, sort, total_hits, returned, retrieved_at
records title, year, doi, arxiv_id, venue, abstract, source_api, query_id
```

DOI 已去掉 `https://doi.org/` 前缀，arXiv ID 已去掉版本号，OpenAlex 的摘要已由倒排索引还原成文本。

### 6.3 `results/merged/merged{suffix}.json`

```text
meta     created_at, script, dedup_rules, inputs, counts, candidates
records  merged_id, title, year, doi, arxiv_id, venue, abstract, id_status, alt_ids, title_linked,
         sources, query_ids, n_queries, n_sources, hits, mean_rank, raw_refs
```

- `id_status`：取值为 `DOI` / `arXiv` / `UNVERIFIED`。
- `raw_refs`：形如 `openalex_Q1#8`，即文件名去掉 `.json`，`#` 后是该条在文件中的名次。
- `merged_id`：编号规则固定，输入不变时编号也不变。

### 6.4 `results/merged/candidates{suffix}.csv`

共 17 列：`rank, merged_id, hits, n_queries, n_sources, mean_rank, query_ids, sources, id_status, doi, arxiv_id, title, year, venue, title_linked, raw_refs, abstract`。编码为带 BOM 的 UTF-8，Excel 可以直接打开。

### 6.5 `evidence/authors{suffix}.json`

```text
meta     source, script, input, top, retrieved_at
records  rank, merged_id, doi, openalex_id, openalex_title, title_matches, authors, n_authors, error
```

### 6.6 `evidence/evidence_table{suffix}.md`

- 表头必须有 `DOI/arXiv`、`verified`；`rank` 和 `题目`（或 `Title`）用于题目比对。
- 五个面的取值只能是 `overlap` / `differ` / `unknown`。
- verified 列格式为"Crossref 结果；落地页结果"，由 `verify.py` 写入。
  - "Crossref HTTP 200 · 题目一致 · …"：DOI 有效，且指向表中这篇；
  - "BLOCKED at <域名>"：该域名不允许访问；
  - "UNVERIFIED"：没有 DOI。

### 6.7 `logs/RUN_LOG.md`

- **只追加**：新条目一律写在末尾，不改写已有条目。
- **条目格式**：以 `---` 分隔，标题写成 `## [YYYY-MM-DD HH:MM UTC] Step N — 标题`，正文包含研究者的要求、命令、输出、产出文件、备注。
- **编号**：下一步是 **Step 24**。
- **旧哈希**：Step 20 之前的条目里引用的是改写历史之前的提交哈希，按 Step 20 的对照表查新哈希。

## 7. 脚本速查

| 脚本 | 作用 | 常用参数 | 访问网络 | 退出码 |
|---|---|---|---|---|
| `search.py` | T3 检索 | `--dry-run`、`--ids`、`--sources`、`--queries`、`--suffix` | api.openalex.org、api.semanticscholar.org | 0 全部成功；1 有请求失败，或 dry-run 发现语法错误；2 检索式文件不合格或参数错误 |
| `merge.py` | T4 合并去重、前 20 候选 | `--suffix` | 无 | 0 成功；没有记录或同一来源混有不同检索方式时报错退出 |
| `authors.py` | T5 查作者 | `--top`、`--candidates`、`--out` | api.openalex.org | 0（单条失败记在 `error` 字段里） |
| `verify.py` | T5 DOI 核验 | `--table` | doi.org、api.crossref.org、出版商网站 | 0 Crossref 全部成功；1 有失败 |
| `logrun.py` | 运行命令并写日志 | `"<步骤名>" -- <命令>` | 无 | 与被运行的命令相同；用法错误时为 1 |

值得知道的常量：

- `search.py`：`TOP_N = 25`，`CONCURRENT_FROM_YEAR = 2023`，`MAX_RETRY_WAIT = 60`，截断词表 `TRUNCATION`；
- `merge.py`：`TOP_K = 20`，`MIN_TITLE_WORDS = 5`，预印本版本规则 `PREPRINT_VERSION_RE`；
- `verify.py`：`TIMEOUT = 30`，`CROSSREF_RETRIES = 5`。

## 8. 已定的设计决策（原因见 RUN_LOG 对应步骤）

| 决策 | 原因 | 见 |
|---|---|---|
| 不判断新颖性 | PROJECT.md 规则 a | Step 0 |
| "AI 工具"只指生成式 AI；检索时保留更宽的 AI 说法，筛选时用 LLM、ChatGPT、Gemini、Claude、OpenAI、Anthropic 等关键词判断 | 研究者决定 | Step 2 |
| Semantic Scholar 用 bulk 接口，不用 relevance search | relevance search 不支持布尔和短语；Q2 退回核心词后，前 25 条里 0 条满足原检索式 | Step 3–4 |
| Semantic Scholar 按被引次数取前 25 条 | bulk 接口没有相关度排序；研究者同意 | Step 4 |
| OpenAlex 用 `title_and_abstract.search` | 默认的 `search=` 匹配全文，前 25 条多数在标题和摘要里不满足检索式 | Step 4–5 |
| OpenAlex 的截断词换成完整词 | OpenAlex 的默认检索不支持通配符 | Step 4 |
| concurrent 只取 2023 年起 | 与"只指生成式 AI"一致 | Step 2 |
| 去重：DOI（含预印本版本后缀）、arXiv ID、至少 5 个词的规范化标题；只靠标题合并的组标 `title_linked` | 预印本与正式版的合并；核对时发现过 OSF 版本漏合并 | Step 5 |
| 命中次数 = 命中的"检索式 × 来源"列表数；同一列表里的多个版本只算一次 | 避免版本多的预印本被高估 | Step 6 |
| DOI 核验 = Crossref 元数据（经 doi.org 内容协商）+ 落地页 | 出版商网站常常拦截脚本；Crossref 能确认 DOI 指向的是哪篇论文 | Step 7–8 |
| 证据表"研究问题"面要求研究对象是科研选题 | 每个面只看自己那一部分 | Step 7 |
| 提交信息不放会话链接；`main` 只通过 PR 修改 | 研究者要求 | Step 19–20 |

## 9. 已知问题与可改进处

1. **召回**：v1 漏检了参考文献（Hao 等，Nature 2026），原因是检索词不匹配（Step 11）。v2 的修正是在知道原因之后做的，所以 v2 检索到它不算独立验证。
2. **噪声**：v2 把 "narrowing of science" 放宽为 narrowing，混进了 "narrow AI" 一类论文（v2 前 10 篇里有 4 篇）。可以让 `search.py` 支持 NOT 来排除，或者换成更具体的短语。
3. **预印本与正式版未合并**：两者题目不同、又没有共同 ID 时不会合并，例如 v2 的 M003 和 M106。
4. **排名靠并列决定**：两轮的前 20 都出自并列组。Semantic Scholar 按被引次数排序，偏向老文献。
5. **没有摘要的记录**：只能靠题目被检索到，也只能靠题目标注。
6. **落地页核验**：在云端被网络策略拦截；本地大多能访问，但出版商常对脚本返回 403。Emerald 和 IEEE 的 DOI 登记的是 `http://` 地址。
7. **arXiv DOI**：这类 DOI 由 DataCite 登记，核验元数据需要能访问 `data.crosscite.org`。
8. **质量检查没有脚本**：检索质量检查（词干还原后满足原检索式的比例）是会话中的内联脚本，没有放进仓库，方法见 Step 4、13、15。可以做成一个可选脚本。
9. **年份**：证据表里的年份取各版本中最早的一个，可能和正式发表年份不同。
10. **待定的标注标准**：研究者对"研究问题"面的标注标准有不同意见，主张去掉情境后看问题是否相同（见 `evidence/difference_statement.md`），还没有落实到 v1、v2 两张证据表。

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
- [ ] `python3 scripts/search.py --dry-run` 显示 `6/6 queries valid`
- [ ] 冒烟测试通过，并删除 `_smoke` 文件
- [ ] 在 ZCode 中让 GLM 读完 `AGENTS.md`、`PROJECT.md`、`HOWTO.md`、`HANDOFF.md`，并复述三条硬规则
- [ ] 开始新想法前，按 `HOWTO.md` 第 1 节先备份、再清空示例产出
