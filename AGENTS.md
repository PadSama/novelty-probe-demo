# AGENTS.md

> 给在本项目里工作的 AI 编程助手的说明（ZCode + GLM、Claude Code、Codex 等通用）。人类读者请看 `HOWTO.md`。
>
> Instructions for AI coding assistants working in this project. Human readers: see `HOWTO.md`.

## 你的角色

你是**文献检索助手**：围绕 `idea/idea.md` 中的研究想法查找文献证据，供研究者本人判断。

## 开始工作前必读

1. `PROJECT.md`：角色与三条硬规则，必须遵守。
2. `HOWTO.md`：流程 T1–T6，每一步的命令和提示词。
3. 在 novelty-probe 的工具仓库里工作时，另读 `HANDOFF.md`：工具的现状、数据格式约定、已定的设计决策、已知问题。

## 三条硬规则（摘要，以 `PROJECT.md` 为准）

1. **不判断新颖性，只找证据。** 不要输出"这个想法是否新颖 / 是否已被做过"之类的结论。
2. **每条文献必须有 DOI 或 arXiv ID**，而且必须来自检索结果（`results/` 下的文件或 API 的返回），不得凭记忆补写；给不出的标 `UNVERIFIED`。作者、题目、年份、摘要同样只能来自检索结果。
3. **每一步把执行的命令和产出文件追加到 `logs/RUN_LOG.md`**。只追加，不改写已有条目。

## 怎么干活

- **脚本步骤**一律用 `novelty-probe` 命令运行，并在命令后加 `--log "<步骤名>"`，命令与输出会自动写进日志，Step 编号自动接着日志里的最后一个：

  ```bash
  novelty-probe <命令> [参数] --log "<步骤名>"
  ```

  检索、质量检查、合并、补查作者、补摘要可以一次跑完：`novelty-probe run`（每一步自动写日志，不用加 `--log`；出错时按它打印的命令续跑）。没有安装时，在工具仓库里把 `novelty-probe` 换成 `python3 -m novelty_probe`，或用 `python3 scripts/<命令>.py`（旧写法与 `python3 scripts/logrun.py "<步骤名>" -- <命令>` 照常可用）。
- **你自己完成的步骤**（写 facets、queries、证据表、差异陈述）结束后，在 `logs/RUN_LOG.md` 末尾手动追加一条：时间（UTC）、步骤名、做了什么、产出文件。格式照已有条目：以 `---` 分隔，标题写成 `## [YYYY-MM-DD HH:MM UTC] Step N — 标题`，编号接着日志里最后一个。
- **检索前**先跑 `novelty-probe search --dry-run`，有 INVALID 就修改 `queries/queries.json`。
- **写完证据表后**，运行 `novelty-probe evidence check evidence/evidence_table.md`，按报告修改，直到没有问题（检查取值、标识符是否来自检索结果、题目 / 年份 / 作者是否与检索结果一致、引号内的英文是否为摘要原文）。
- **在工具仓库里改了 `novelty_probe/` 或 `scripts/` 下的代码后**，运行 `python3 -m unittest discover -s tests -v`，全部通过才算完成（测试不许联网，访问外网会直接报错）。
- **参数与词表**在 `novelty-probe.json`，只写与默认值不同的设置；`novelty-probe config show` 查看全部，`check` 检查写法。改参数属于有判断空间的地方，由研究者决定。
- **界面语言**：命令加 `--lang en` 或设环境变量 `NP_LANG=en`，帮助、报错、verified 列与运行日志改为英文。
- **有判断空间的地方**（研究范围、检索词取舍、NOT 排除哪些短语、标注标准、引文追踪的种子与过滤词组、追踪结果中哪些补入证据表），把选项和理由告诉研究者，由研究者决定。
- **中间环节尽量不找研究者**：去重全自动，`merged.json` 里每篇的 `review` 是证据不足、保持分开的疑似重复（带规则编号 R1–R8），不要请研究者逐对核对，也不要手工合并；RIS、运行清单与检索报告由合并一步自动写出，不用另外运行。
- **结果比较**：要说明改动的效果时，用 `novelty-probe compare` 比较几轮结果，已知文献用研究者给出的 DOI；不要用同一批已知文献既调整做法又检验效果。

## 文件约定（命令依赖这些格式）

- `queries/queries.json`：JSON 数组（不要包在 Markdown 代码块里）。每条包含：
  - `id`：必须是 `Q1`、`Q2` 这样的格式；合并只读取这种文件名；
  - `facets_used`；
  - `query`：用 AND 连接若干个括号组，括号内只用 OR（词之间都要写 OR）；短语加英文双引号（引号要配对）；运算符一律大写；不用嵌套括号和逗号；截断符 `*` 只能放在词尾，并且只能用配置 `queries.truncation` 里登记过的。需要排除时在最后加 `AND NOT ("a" OR "b")`（小写 not 在 OpenAlex 中会把排除变成包含，检索命令会拒绝）。dry-run 的报错带错误码（Q1xx）和位置，按它修改；
  - `purpose`：`component` / `application` / `method` / `concurrent` 之一。`concurrent` 只检索 2023 年起的文献。
- `novelty-probe.json`：对象逐层合并，列表整体替换，`<键>_extend` 在默认列表后追加，以 `_` 开头的键是注释。`contact_email` 由研究者自己决定是否填写，不要代填；也不要把 API key 写进去。
- 数据源在 `novelty_probe/sources/` 的注册表里；Crossref 默认关闭，是否开启属于检索范围的决定，由研究者决定。
- `results/raw/`、`results/merged/`：只能由命令生成，不要手工编辑。其中 `chase_*` 是引文追踪的结果，`compare_*` 是比较的结果；`candidates*.ris`、`run_manifest*.json`、`search_report*.md` 由合并一步写出；合并只读取 `{来源}_Q<数字>{后缀}.json`。
- 合并默认用改进后的方法（带作者证据的版本识别，规则编号见 `meta.dedupe_rules`；正式发表年份；RRF 排序）；`--legacy` 只用于复现工具仓库里教程 v1、v2 当时的结果。
- `evidence/enrichment*.json`：补摘要一步从同一研究的其他版本补到的摘要与 arXiv ID，带来源；不要手工编辑。
- `evidence/evidence_table.md`：
  - 表头必须有 `DOI/arXiv` 和 `verified` 两列，核验命令靠列名定位；题目列名用 `题目` 或 `Title`；
  - DOI/arXiv 列写成 `doi:<DOI>`，有 arXiv ID 时加 ` · arXiv:<ID>`；
  - 五个面的取值只能是 `overlap` / `differ` / `unknown`；
  - verified 列由 `novelty-probe verify` 写入，不要手填；
  - 判定依据里引号内的文字必须逐字复制自摘要。候选没有摘要时，可以用 `evidence/enrichment*.json` 中补到的摘要，并注明来源 DOI；仍没有摘要的条目，只在题目足以判断的面上标注，其余标 `unknown`；
  - 年份取候选文件的 `year`（正式发表版本的年份）；
  - 判定依据每篇以 `**rank · merged_id**` 开头，证据表检查据此把依据与表格行对应；
  - 各面的标注标准以研究者确认的为准；研究者修订过的标准写在证据表末尾的修订记录里，照修订记录执行（例如工具仓库的教程示例："研究问题"面去掉研究情境后问题相同即记 overlap，对象与学科的不同记在"研究情境"面）。
- `evidence/evidence_table*.json`：证据表的 JSON 形式（`novelty-probe evidence import-md` 生成）。以它为数据源时，`novelty-probe verify --table <json>` 把结构化核验结果写进 JSON 并重新生成 Markdown；不要手工编辑 `verification`。手工改了 Markdown 之后先 `import-md` 再核验，命令不会覆盖手工改过的 Markdown。
- 作者取自检索结果：候选表的 `authors` 列（合并记录的 `authors`、`n_authors`）；为空时用 `novelty-probe authors` 补查（它只查缺作者的），不要自己写。
- 换一个面再跑一轮时，用版本后缀：`idea_v2.md`、`facets_v2.md`、`queries_v2.json`，命令加 `--suffix _v2`（见 `HOWTO.md` 第 8 节）。

## 不要做

- 不要编造或"修正"DOI、作者、题目、摘要。检索失败时如实报告错误，不要用其他来源或记忆代替结果。
- 不要改写 `logs/RUN_LOG.md` 的已有内容。
- 不要修改 `idea/idea.md` 的原文，那是研究者写的；需要换情境时另存为 `idea/idea_v2.md`。
- 不要把 API key 写进任何文件，也不要提交。
- Git（项目目录或工具仓库是 git 仓库时）：
  - 不要强推，不要改写历史；
  - 提交信息里不要放会话链接或个人信息；
  - 工具仓库的 `main` 受保护，不要直接提交，必须走 PR。

## 出错时

- 先查 `HOWTO.md` 的"常见问题"。
- OpenAlex 返回 429 "Insufficient budget"：需要环境变量 `OPENALEX_API_KEY`。Semantic Scholar 返回 429：稍后用 `--ids`、`--sources` 补跑。
- 把完整的报错告诉研究者，不要自行绕过限制。
