# 交接文档：novelty-probe 工具仓库

> **写给**：在本地（如 ZCode + GLM 5.3）接手本仓库的研究者本人，以及在仓库里工作的 AI 助手。
>
> **范围**：项目现状、本地环境准备、在 ZCode 里的用法、数据格式约定、命令速查、已定的设计决策、已知问题、Git 与发布流程、检查清单。操作步骤见 `HOWTO.md`，AI 助手的行为规则见 `AGENTS.md` 与 `PROJECT.md`，各版本的变化见 `CHANGELOG.md`。

## 1. 项目是什么

一个围绕研究想法检索文献证据的流程：

1. 把想法拆成五个面（研究问题、作用机制、研究情境、数据与方法、预期发现）；
2. 组合布尔检索式，检索 OpenAlex 和 Semantic Scholar；
3. 合并去重（识别预印本与正式版），按相关度排序，对前 10 篇候选逐面标注 overlap / differ / unknown；
4. 用 Crossref（查不到时用 OpenAlex）核验每个 DOI；
5. 可选：从证据表中的相关文献出发做引文追踪，补关键词检索因措辞不同而漏掉的文献。

流程**不判断新颖性**，只整理可核验的证据，由研究者判断。

v2.0.0 起它是可安装的命令行工具 `novelty-probe`：工具装一次；每个想法一个项目目录（`novelty-probe init`），研究想法与结果留在研究者自己的目录里；脚本步骤一条命令跑完（`novelty-probe run`）。本仓库的根目录本身也是一个项目目录，放着教程示例（v1、v2、v1b、v2b）。

## 2. 当前状态

| 项目 | 状态 |
|---|---|
| 仓库 | https://github.com/PadSama/novelty-probe-demo （公开，MIT 许可证） |
| 发布 | v1.0.0（标签打在 3f00b7a）；**v2.0.0**（2026-11-03 发布，标签 `v2.0.0` 指向 5c0ed59；发布页面上目前标为 pre-release）。安装与配置见第 3 节 |
| v1.0.0 之后的改动 | 见 `CHANGELOG.md`：针对遗留问题的改进（Step 24–64，见 `docs/IMPROVEMENT_PLAN.md`）与工具层迭代阶段 0–5（Step 66 起，计划与进度见 `docs/ROADMAP.md`，设计理由见 `docs/ARCHITECTURE_REVIEW.md`） |
| 默认分支 | `main`，受规则集保护：禁止删除、禁止强推、必须通过 PR 合并（审批人数 0） |
| 引用信息 | `CITATION.cff`：作者 Yuan, Quan；ORCID 0009-0009-3011-3739；version 2.0.0 |
| 示例运行 | v1（未限定学科）与 v2（管理学与经济学）两轮的全部产出都在仓库里（用旧方法生成，`merge.py --legacy` 可逐字节复现）；v1b、v2b 是用改进后的流程重跑的评估轮（检索、合并、补摘要、引文追踪与比较，没有证据表）；全过程见 `logs/RUN_LOG.md` Step 0–65 |

## 3. 本地环境准备（v2.0.0）

本节写给在本地 ZCode 里替研究者安装、配置 novelty-probe 的 AI 助手（如 GLM），也可以照着手工做。这里只做安装、配置与不联网的检查，**不检索任何研究想法**。实测情况（Step 92）：

- 发布的压缩包（方式 B）与克隆的可编辑安装（方式 A）在 Python 3.9 的虚拟环境里实测，setuptools 为 80.9；
- 不安装的方式 C 在 Python 3.13 上实测；
- 旧版 setuptools（68）会报 3.11 表里第一行的错误；
- Windows 上 `novelty-probe` 的各命令由 CI 用 PowerShell 检查；建虚拟环境的 PowerShell 写法是 Python 的标准用法，未在本沙箱运行。

### 3.1 选一种安装方式

| 方式 | 适合 | 要点 |
|---|---|---|
| **A. 从本地克隆安装（推荐）** | 本机已有本仓库的克隆，或能用 git | 可编辑安装，以后 `git pull` 即更新；仓库里的离线自检可以运行 |
| **B. 从发布的压缩包安装** | 只用工具、不看源码 | 不需要 git；压缩包只含工具本身 |
| **C. 不安装** | 连不上 PyPI、装不了包时的后备 | 解压或克隆后直接运行，见 3.4 的 C |

A、B 两种都要从 PyPI（或镜像）取构建工具 setuptools 77 或更新的版本。连不上 PyPI 时用 3.3 里的镜像，或改用 C。

### 3.2 前提

- **Python 3.9 或更高**：macOS / Linux 运行 `python3 --version`，Windows 运行 `py -3 --version`。
- 方式 A 需要 git（`git --version`）。
- **不要用系统自带的 pip 直接装进系统 Python**：一律装进 3.3 的虚拟环境。这样能避开 `externally-managed-environment` 与旧版 pip、setuptools 的问题。

### 3.3 建虚拟环境，升级 pip 与 setuptools（只做一次）

macOS / Linux：

```bash
python3 -m venv ~/.venvs/novelty-probe
```

```bash
source ~/.venvs/novelty-probe/bin/activate
```

```bash
python -m pip install --upgrade pip "setuptools>=77"
```

Windows PowerShell：

```powershell
py -3 -m venv $HOME\.venvs\novelty-probe
```

```powershell
& $HOME\.venvs\novelty-probe\Scripts\Activate.ps1
```

```powershell
python -m pip install --upgrade pip "setuptools>=77"
```

- PowerShell 拒绝运行 `Activate.ps1` 时，先运行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`；也可以不激活，直接用 `$HOME\.venvs\novelty-probe\Scripts\novelty-probe.exe`。
- 激活只对当前终端有效。新开的终端（包括 ZCode 新开的终端）要再激活一次，或直接写虚拟环境里的完整路径。
- PyPI 慢或连不上时（中国大陆的网络常见），在每条 `pip install` 命令后加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`。安装本包时 pip 也要从同一个地址取 setuptools。

### 3.4 安装

**A. 从本地克隆安装**（在激活了虚拟环境的终端里）：

```bash
git clone https://github.com/PadSama/novelty-probe-demo.git
```

已有克隆时不必再克隆。先进入克隆目录，确认没有本地改动：`git status` 应显示 `nothing to commit`。有改动时先告诉研究者，不要覆盖，然后：

```bash
git checkout main
```

```bash
git pull
```

```bash
python -m pip install -e .
```

`main` 上 v2.0.0 之后的提交只改文档。要装与发布完全相同的版本，先 `git checkout v2.0.0` 再安装。

**B. 从发布的压缩包安装**：

```bash
python -m pip install "https://github.com/PadSama/novelty-probe-demo/archive/refs/tags/v2.0.0.zip"
```

下载失败时，在浏览器里打开该地址或仓库的 Releases 页面下载压缩包，再安装本地文件：

```bash
python -m pip install ./novelty-probe-demo-2.0.0.zip
```

**C. 不安装**：解压压缩包或使用克隆，不需要 pip。

- 在工具目录里，用 `python3 -m novelty_probe <命令>`（Windows：`py -3 -m novelty_probe <命令>`）代替 `novelty-probe <命令>`。
- 在其他目录（如项目目录）里，用 `python3 <工具目录>/scripts/<命令>.py …`，例如 `python3 <工具目录>/scripts/init.py my-idea`。

### 3.5 检查安装

```bash
novelty-probe --version
```

应显示 `novelty-probe 2.0.0`。提示找不到命令时，说明虚拟环境没激活，或安装目录不在 PATH 里：

- 激活虚拟环境；
- 或改用 `python -m novelty_probe --version`（已安装时在任何目录都可用）。

### 3.6 API key（只放在环境变量里）

| 变量 | 是否必需 | 说明 |
|---|---|---|
| `OPENALEX_API_KEY` | 实际上必需 | 免费申请：https://help.openalex.org/api/authentication/ 。没有 key 时共用每日额度，很容易遇到 429 |
| `S2_API_KEY` | 可选 | https://www.semanticscholar.org/product/api#api-key-form 。有 key 时的限额是**每秒 1 个请求，所有接口合计**；检索命令对发往 S2 的每个请求（含翻页与重试）统一节流，不要同时运行两个访问 S2 的命令 |

key 由研究者自己设置。助手不要把 key 写进任何文件（包括 `novelty-probe.json`），也不要在终端或日志里显示 key 的值。

- **macOS / Linux**：把 `export OPENALEX_API_KEY="…"` 写进 shell 的启动文件（zsh：`~/.zshenv` 或 `~/.zshrc`；bash：`~/.bashrc`）。
- **Windows**：在 PowerShell 里运行 `setx OPENALEX_API_KEY "…"`。

设置后**完全退出并重新打开 ZCode**，新的环境变量才会传给它。在 ZCode 的终端里用下面这条命令核对，它只显示是否已设置，不显示值：

```bash
python -c "import os; print({k: bool(os.environ.get(k)) for k in ('OPENALEX_API_KEY', 'S2_API_KEY')})"
```

### 3.7 网络

- **需要访问的域名**：在自己电脑上通常不用设置。必须能访问 `api.openalex.org`、`api.semanticscholar.org`、`doi.org`、`api.crossref.org`。以下两项可选：
  - `data.crosscite.org`：arXiv 等 DataCite DOI 在 Crossref 查不到时，核验命令会改查 OpenAlex；
  - 出版商网站：用于核验落地页。
- **需要代理的网络**：设置 `HTTPS_PROXY`。命令用 Python 标准库 `urllib`，会自动读取这个变量。
- **macOS 证书问题**：用 python.org 安装包装的 Python，可能报 `CERTIFICATE_VERIFY_FAILED`。运行 `/Applications/Python 3.x/Install Certificates.command` 即可。

### 3.8 离线自检（方式 A，在克隆目录里）

```bash
python -m unittest discover -s tests -v
```

应显示 `OK (skipped=6)`，用时二十秒左右。测试不联网，也不改动仓库文件；跳过的 6 项是联网接口检查（3.10）。

- 测试件读 `examples/tutorial/` 下的教程产出副本。其中一项按旧方法（`merge --legacy`）重跑合并，再和已提交的 v1、v2 合并结果逐字节比较。
- 回放测试用 `tests/fixtures/cassettes/` 里录制的真实响应，跑完 search / verify / snowball 的主流程，并在临时项目里从头跑一遍 `novelty-probe init` 与 `novelty-probe run`。
- 测试里装有网络护栏（`tests/netguard.py`）：除本机回环地址外，任何 DNS 查询或连接都会直接报错，子进程同样如此。
- GitHub Actions（`.github/workflows/tests.yml`）在 Python 3.9–3.13 × Ubuntu / Windows 上跑同一套测试，再安装本包，并用安装后的命令走一遍新项目。2026-11-03 起不再测试 macOS（研究者决定：macOS 节点排队常卡住、额度消耗快）。

压缩包（方式 B、C）里没有测试件，不能运行离线自检；用 3.9 的冒烟测试代替。

### 3.9 不联网的冒烟测试（在仓库之外的临时目录里做，做完删除）

```bash
novelty-probe init ../np-smoke
```

把教程的检索式复制进去，作为语法检查的样例：方式 A 在克隆目录里取 `examples/tutorial/queries/queries.json`；方式 B、C 可以手写一条，如 `[{"id": "Q1", "facets_used": [], "purpose": "component", "query": "\"large language models\" AND homogenization"}]`。然后：

```bash
novelty-probe config check --root ../np-smoke
```

```bash
novelty-probe search --dry-run --root ../np-smoke --log "检查检索式"
```

```bash
novelty-probe run --dry-run --root ../np-smoke
```

应依次看到：
- `检查通过`；
- `1/1 queries valid` 或 `6/6 queries valid`，以及请求估算；
- `run` 六个步骤的命令。

`../np-smoke/logs/RUN_LOG.md` 里应有 Step 0 与 Step 1 两条。最后删除整个临时目录：macOS / Linux 用 `rm -rf ../np-smoke`，PowerShell 用 `Remove-Item -Recurse -Force ..\np-smoke`。冒烟测试只是检查环境，不属于研究步骤，不写进仓库的 RUN_LOG。

### 3.10 联网接口检查（可选，方式 A；只发 6 个请求，不检索研究想法）

确认 key 与网络可用，以及 OpenAlex、Semantic Scholar、Crossref 的接口行为仍与命令的假设一致。

```bash
NP_LIVE=1 python -m unittest tests.test_live_contract -v
```

```powershell
$env:NP_LIVE = "1"; python -m unittest tests.test_live_contract -v
```

### 3.11 安装与配置的常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `` `project.license` must be valid exactly by one definition `` | setuptools 低于 77：多见于加了 `--no-build-isolation`，或环境里是旧版 setuptools | 在虚拟环境里 `python -m pip install --upgrade pip "setuptools>=77"`；安装时不要加 `--no-build-isolation` |
| `Could not find a version that satisfies the requirement setuptools>=77`，或下载超时 | 连不上 PyPI | pip 命令加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`；或用 3.4 的方式 C |
| `externally-managed-environment` | 系统 Python 不允许直接装包 | 用 3.3 的虚拟环境 |
| pip 提示可编辑安装需要 `setup.py` | pip 低于 21.3，不支持只有 `pyproject.toml` 的可编辑安装 | 先升级 pip（3.3），或去掉 `-e` |
| `novelty-probe: command not found`，或 PowerShell 无法识别 | 虚拟环境没激活，或安装目录不在 PATH 里（pip 会提示 `… is not on PATH`） | 激活虚拟环境；或用 `python -m novelty_probe` |
| PowerShell 拒绝运行 `Activate.ps1` | 执行策略 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`，或直接用 `…\Scripts\novelty-probe.exe` |
| 下载 GitHub 压缩包失败 | 网络 | 浏览器下载后安装本地文件，或用克隆（方式 A） |
| `找不到项目目录` / `No project folder found` | 当前目录不是项目目录 | 进入项目目录，或加 `--root`；还没有项目时先 `novelty-probe init` |
| 核对 key 时显示 `False` | ZCode 没有拿到环境变量 | 写进 shell 的启动文件，或用 `setx`，然后完全退出并重开 ZCode |
| `CERTIFICATE_VERIFY_FAILED`（macOS） | python.org 的 Python 没装证书 | 运行 `Install Certificates.command`（见 3.7） |

## 4. 在 ZCode 里使用 GLM

1. **安装与配置**：在 ZCode 中打开本仓库的克隆目录（方式 A），确认 GLM 读到了 `AGENTS.md`。第一条消息建议这样写，让它先装好、查好再报告，不做任何检索：

   ```text
   请先阅读本仓库的 AGENTS.md、PROJECT.md、HOWTO.md、HANDOFF.md，然后按 HANDOFF.md 第 3 节在本机安装并检查 novelty-probe v2.0.0：
   1) 复述 PROJECT.md 的三条硬规则；
   2) 报告 Python 版本；按 3.3 建虚拟环境并升级 pip 与 setuptools（连不上 PyPI 时加 3.3 里的镜像地址）；
   3) 按 3.4 的方式 A 从本仓库安装，运行 novelty-probe --version，应显示 2.0.0（你的每条命令若在新的终端里运行、激活保不住，就写虚拟环境里的完整路径，如 ~/.venvs/novelty-probe/bin/python，Windows 为 $HOME\.venvs\novelty-probe\Scripts\python.exe）；
   4) 用 3.6 的命令核对 OPENALEX_API_KEY、S2_API_KEY 是否已设置：只报告是否已设置，不要显示它们的值，也不要把 key 写进任何文件；
   5) 运行 3.8 的离线自检；再按 3.9 在仓库之外做不联网的冒烟测试，做完删除临时目录。
   不要运行任何检索，不要改动仓库里的文件。每一步把命令和输出原样告诉我；遇到报错先查 HANDOFF.md 3.11 与 HOWTO.md 的"常见问题"，把完整报错告诉我，不要自行绕过。
   ```

2. **开始一个研究想法时**（以后）：在仓库之外 `novelty-probe init <目录>`，然后在 ZCode 中打开这个新目录。GLM 在那里读到的是项目自己的 `AGENTS.md`、`PROJECT.md`、`HOWTO.md`，流程见该目录的 `HOWTO.md`。

3. 需要助手完成的步骤是：
   - T2：拆面与检索式；
   - T5：证据表标注；
   - T6 第 1 节：选出最接近的三篇。

   提示词在 `HOWTO.md` 第 3、6、7 节，中英文任选。T5b 引文追踪的种子和过滤词组由研究者决定，助手只运行命令、整理结果。

4. 脚本步骤可以让助手执行，也可以自己在终端执行：一次跑完用 `novelty-probe run`；单独运行某一步时，命令后加 `--log "<步骤名>"`。

5. 每一步结束后检查三件事：命令和产出是否写进了 RUN_LOG；DOI、作者是否都来自检索结果；有没有出现新颖性结论。

**换用 GLM 后要特别留意的地方**（都来自本项目实际遇到过的问题，前三条已由检索命令自动检查，第四条由核验命令检查）：

- 助手可能把 JSON 包在 Markdown 代码块里写进 `queries.json`，检索命令会报"不是合法的 JSON"；
- `id` 必须是 Q1–Q6 这样的格式，`purpose` 必须是四个取值之一；
- 检索式里不能有未登记的截断符 `*` 和逗号；运算符必须大写，排除只能写成 `AND NOT (…)` 放在最后（小写 not 在 OpenAlex 里会把排除变成包含，检索命令会拦截）；
- 证据表的列名必须完全一致（`DOI/arXiv`、`verified`），否则核验命令找不到列；
- 判定依据的引文必须逐字来自摘要；作者取自检索结果（候选表的 `authors` 列），为空时用 `novelty-probe authors` 补查，不能凭记忆写。

## 5. 结构与数据流

```text
novelty-probe init <目录> ──► PROJECT.md、AGENTS.md、HOWTO.md、idea/idea.md（模板）、novelty-probe.json、logs/RUN_LOG.md
  ▼
idea/idea.md
  │  T2 AI 助手
  ▼
facets/facets.md + queries/queries.json
  │  T3 novelty-probe search（run 的 check、search 两步）：检索式解析为语法树（novelty_probe/query.py），按数据源注册表（novelty_probe/sources/）逐个检索
  │      ──► OpenAlex（title_and_abstract.search）、Semantic Scholar（bulk）；Crossref 可选，默认关闭
  ▼
results/raw/{来源}_{Qn}{后缀}.json        每条检索式 × 每个来源，前 25 条（S2 取回全部命中后本地重排），带作者
  │  novelty-probe qa（run 的 qa 一步）：标题 + 摘要满足检索式的比例；本地匹配的偏差
  │  T4 novelty-probe merge（run 的 merge 一步）：DOI / arXiv ID 去重 → 版本识别（作者作证据；规则编号 D1–D5 / R1–R8）→ RRF 排序
  ▼
results/merged/merged{后缀}.json + candidates{后缀}.csv（前 20 篇，带作者）
  + candidates{后缀}.ris（导入文献管理软件）+ run_manifest{后缀}.json + search_report{后缀}.md（PRISMA-S 风格）
  │  T5 novelty-probe enrich（run 的最后一步）──► OpenAlex title.search（同一研究的其他版本）
  │  T5 novelty-probe authors（run 只在缺作者时运行）──► OpenAlex /works/doi:
  ▼
enrichment.json（+ authors.json）──► AI 助手标注 ──► evidence/evidence_table.md（可选导入为 .json）
  │  T5 novelty-probe evidence check：取值、标识符来自检索结果、题目 / 年份 / 作者、引文是摘要原文
  │  T5 novelty-probe verify ──► doi.org → Crossref 元数据（失败时 OpenAlex）；doi.org → 出版商落地页
  ▼
verified 列写回证据表
  │  T5b（可选）novelty-probe snowball ──► OpenAlex referenced_works / cites:
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
| `results/merged/candidates*.csv` | 前 20 篇候选（带作者） | `merge.py` | `authors.py`、`enrich.py`、T5 标注 |
| `results/merged/candidates*.ris` | 候选的 RIS（Zotero、EndNote 可导入） | `merge.py`（其他范围用 `export.py`） | 研究者 |
| `results/merged/run_manifest*.json` | 运行清单：输入输出文件的哈希、检索式与日期、配置指纹、版本 | `merge.py` | `report.py`、研究者 |
| `results/merged/search_report*.md` | 检索报告（PRISMA-S 风格，可作方法部分的底稿） | `merge.py`（`report.py render` 可换语言重新生成） | 研究者 |
| `evidence/authors*.json` | 候选的作者（检索结果缺作者时补查） | `authors.py` | T5 标注、`evidence.py` |
| `evidence/enrichment*.json` | 从其他版本补到的摘要、arXiv ID（带来源） | `enrich.py` | T5 标注 |
| `results/raw/chase_*.json`、`results/merged/chase_*.csv` | 引文追踪结果 | `snowball.py` | 研究者、`compare.py` |
| `results/merged/compare_*.json` | 几轮结果的比较 | `compare.py` | 研究者 |
| `docs/IMPROVEMENT_PLAN.md` | 遗留问题的调研、计划与评估 | AI 助手 | 研究者 |
| `evidence/evidence_table*.md` | 逐面标注与 DOI 核验 | AI 助手 + `verify.py` | 研究者、T6 |
| `evidence/difference_statement.md` | 差异陈述 | AI 助手（第 1 节）+ 研究者（第 2、3 节） | 研究者 |
| `logs/RUN_LOG.md` | 只追加的运行日志 | `novelty-probe init`（Step 0）、`run`、`--log`、`logrun` + AI 助手 | 所有人 |
| `novelty-probe.json` | 项目配置（只写与默认值不同的设置） | 研究者（`novelty-probe init` 或 `novelty-probe config init` 生成最小文件） | 所有脚本 |
| `evidence/evidence_table*.json` | 证据表的 JSON 形式（可选；以它为数据源时 Markdown 由它生成） | `evidence.py import-md`、`verify.py --table *.json` | `evidence.py`、`verify.py`、`snowball.py` |
| `novelty_probe/` | 包：`cli.py`（`novelty-probe` 命令的入口与命令表）、`commands/`（每个命令一个模块，原 `scripts/*.py` 的代码）、`templates/`（`novelty-probe init` 写入的文档与想法模板）、`query.py`（检索式语法树与错误码）、`sources/`（数据源协议与注册表：`openalex.py`、`semanticscholar.py`、`crossref.py`、本地重排 `localrank.py`）、`text.py`（文本匹配）、`record.py`（合并记录的组装）、`dedupe.py`（去重规则）、`rank.py`（RRF 与 BM25）、`export.py`（RIS）、`report.py`（运行清单与检索报告）、`http.py`（客户端）、`cache.py`、`schemas.py`（响应形状校验）、`config.py`、`i18n.py`、`runtime.py`（通用参数）、`evidence.py`、`verification.py`、`defaults.py`、`io.py`、`paths.py` | — | 所有脚本 |
| `scripts/*.py` | 1.x 的命令入口，转发到 `novelty-probe <命令>`；旧命令照常可用 | — | 不安装时运行命令 |
| `pyproject.toml` | 包的元数据（无依赖；版本取自 `novelty_probe.__version__`；命令 `novelty-probe`） | — | `pip install` |
| `CHANGELOG.md` | 各版本的变化 | — | 研究者、发布说明 |
| `tests/` | 离线自检：`test_offline`、`test_pipeline`、`test_core`、`test_http`、`test_replay`、`test_config`、`test_evidence`、`test_query_sources`、`test_records`、`test_cli`；`test_live_contract`（NP_LIVE=1 才运行）；`tests/fixtures/` 为词干还原对照表与录制件 | — | 改代码后运行 |

## 6. 数据格式约定

### 6.1 `queries/queries.json`

JSON 数组，每条形如：

```json
{"id": "Q1", "facets_used": ["mechanism", "context"], "query": "(\"large language models\" OR \"generative AI\") AND (homogenization OR \"collective diversity\")", "purpose": "component"}
```

- **语法**：用 AND 连接若干个括号组，括号内只用 OR；短语加英文双引号；运算符一律大写；不用嵌套括号和逗号。排除写成 `AND NOT ("a" OR "b")`，放在包含组之后：OpenAlex 原样发送（脚本核对 OpenAlex 返回的解析树，NOT 丢失或分组改变都报错不保存），S2 译为 `+ -(…)`。小写的 and / or / not 和以 `-`、`!` 开头的词会被拒绝（OpenAlex 把小写 not 当普通词，实测会把排除变成必须包含）。
- **解析**：`novelty_probe/query.py` 把检索式解析为语法树，各数据源从同一棵树序列化。错误有固定错误码与位置：Q101 嵌套括号、Q102 括号不配对、Q103 括号内的 AND、Q104 括号外的 OR、Q105 以 NOT 开头、Q106 NOT 的位置、Q107 小写运算符、Q108 用 - 或 ! 排除、Q109 空的组、Q111 逗号、Q112 引号不配对、Q113 空短语、Q114 截断符不在词尾、Q115 括号内缺少 OR、Q116 组之间缺少 AND、Q117 OR 一侧没有词；Q201 未登记的截断词（OpenAlex、Crossref 序列化时）。Q111–Q117 是阶段 3 起才拒绝的写法：它们以前会让各来源检索到不同的内容。
- **检查**：`search.py` 的 `load_queries()` 检查 JSON 格式、id 格式与是否重复、query 是否为空、purpose 取值；`--dry-run` 另外检查检索式语法（错误位置用 ^ 标出），打印启用的各来源实际会发送的检索串与请求估算。
- **截断词**：只有配置 `queries.truncation` 中登记过的截断词才能用（如 `bibliometric*`），其他截断词会报错（Q201）。HOWTO 的提示词要求不用截断，这样最省事。

### 6.2 `results/raw/{source}_{id}{suffix}.json`

```text
{"meta": {...}, "records": [...]}
meta    source_api, query_id, purpose, queries_file, query_original, year_from, conversion, query_sent,
        api_interpretation（仅 OpenAlex）, request_url, sort, total_hits, returned, retrieved_at
records title, year, doi, arxiv_id, venue, abstract, authors, n_authors, source_api, query_id
        S2 记录另有 local_rank：groups_matched, bm25, has_abstract, citations（及 same_title_dropped）
```

`authors` 为作者名列表（按来源给出的顺序，最多 20 位），`n_authors` 为作者总数；阶段 4 之前检索的文件没有这两个字段，读取时按 `None` 处理。

DOI 已去掉 `https://doi.org/` 前缀，arXiv ID 已去掉版本号，OpenAlex 的摘要已由倒排索引还原成文本。S2 的 meta 另有 `retrieval_sort` 与 `pool`（取回条数、页数、是否截断、有摘要的条数、去掉的同题记录数）。旧结果（v1、v2）没有这些字段。

Crossref 的结果文件（`crossref_{id}{suffix}.json`，开启后才有）：记录格式相同（`arxiv_id` 总是空，题目与摘要去掉了 JATS 标签），另有 `local_rank`；meta 另有 `lossy`（有损之处）与 `pool`（取回条数、页数、是否截断、有摘要的条数、跳过的条目类型数、本地满足检索式的条数 `conforming`、去掉的同题记录数）。`total_hits` 是 Crossref 对词袋的命中数，与布尔检索的命中数不可比。

### 6.3 `results/merged/merged{suffix}.json`

```text
meta     schema（novelty-probe/merged@2）, created_at, script, method, year, parameters, config_file, config_hash,
         inputs, counts, dedupe_rules, version_links, review_pairs, bm25_terms, ignored_phrases, candidates
records  merged_id, title, year, doi, arxiv_id, venue, abstract, id_status, alt_ids, title_linked, sources, query_ids,
         n_queries, n_sources, hits, mean_rank, raw_refs, year_first, authors, n_authors, field_source, review,
         dedupe_rules, rrf, bm25, n_conform
```

- `id_status`：取值为 `DOI` / `arXiv` / `UNVERIFIED`。
- `raw_refs`：形如 `openalex_Q1#8`，即文件名去掉 `.json`，`#` 后是该条在文件中的名次。
- `merged_id`：编号规则固定，输入不变时编号也不变。
- `year`：正式发表版本的年份；`year_first`：最早版本的年份。
- `authors`、`n_authors`：第一条带作者的原始记录的作者（最多 20 位）与作者总数；原始记录都没有作者时为 `null`。
- `field_source`：标题、年份、DOI、arXiv ID、出处、摘要、作者各取自哪条原始记录（形如 `openalex_Q1#3`）。
- `dedupe_rules`：并成这一篇所用的规则编号（D1 同一 DOI；D2 预印本版本 DOI；D3 同一 arXiv ID；D4 规范化题目相同；D5 题目几乎相同且有共同作者），含义写在 meta 的 `dedupe_rules`。
- `review`：[{with, rule, reason}]，疑似同一研究、但证据不足而保持分开（R1 一方带通知/变体词；R2 两个不同的正式 DOI；R3 数据仓储 DOI；R4 年份差超过窗口；R5 摘要不同；R6 题目几乎相同、作者证据不足；R7 题目相同、作者没有共同的名字；R8 合并组超过上限）。只记录，不需要人工核对。
- `rrf`、`bm25`、`n_conform`（本地判断满足几条检索式）：排序用。
- schema 1（阶段 3 及以前的默认方法）没有 `schema`、`authors`、`n_authors`、`field_source`、`dedupe_rules`，`review` 没有 `rule`；读取方都按缺省处理。没有作者的旧数据重新合并，除这些新增字段外与阶段 3 相同（`tests/test_records.py` 固定了 v1、v2 的校验值）。`--legacy` 的输出与旧格式完全相同。

### 6.4 `results/merged/candidates{suffix}.csv`

默认方法共 23 列：`rank, merged_id, rrf, bm25, n_conform, hits, n_queries, n_sources, mean_rank, query_ids, sources, id_status, doi, arxiv_id, title, authors, year, year_first, venue, title_linked, review, raw_refs, abstract`；`--legacy` 为原来的 17 列（无 `rrf, bm25, n_conform, authors, year_first, review`）。`authors` 为前 3 位作者，超过 3 位加 et al.（与证据表的写法相同）；`review` 每项写成 `M012 (R6): 原因`。编码为带 BOM 的 UTF-8，Excel 可以直接打开。读取方（`authors.py`、`enrich.py`）按列名取值，各种格式都能用。

### 6.4a `results/merged/candidates{suffix}.ris`

RIS（带 BOM 的 UTF-8，CRLF 换行；`.gitattributes` 不改换行）。每条：TY（有正式发表 DOI 为 JOUR，只有预印本 DOI 或 arXiv ID 为 UNPB，都没有为 GEN）、TI、AU（每位一行）、PY、T2（出处）、DO、UR（DOI 与 arXiv 链接）、AB、KW（证据表导出时为各面的标注）、N1（来自哪些检索式与来源、RRF、合并规则；作者被截断时注明"first 20 of N authors"）、ID（merged_id）、ER。值都取自检索结果。`export.py --all` 导出全部合并记录（`merged{suffix}.ris`），`--evidence <表>` 导出证据表各行（`<表>.ris`）。

### 6.4b `results/merged/run_manifest{suffix}.json` 与 `search_report{suffix}.md`

```text
schema      novelty-probe/manifest@1
tool        novelty_probe（版本）, python, platform
config      file, hash
method, parameters
searches    [{file, sha256, source, query_id, purpose, query_original, query_sent, year_from, retrieved_at,
              http_mode, conversion, total_hits, returned, warnings, config_hash}]
outputs     [{file, sha256}]（merged、candidates.csv、candidates.ris）
counts      raw_records, merged_records, duplicates_removed, dedupe（id_links / version_links / kept_separate 各规则次数）,
            with_authors, id_status, local_match（各来源：with_abstract, conforming, nonconforming_share）
candidates  top_k, sort, items[{merged_id, doi, arxiv_id, title}]
```

检索报告由清单生成（`report.py render <清单> --lang en` 可换语言），各节参照 PRISMA-S（Rethlefsen et al. 2021, doi:10.1186/s13643-020-01542-z）：数据库与接口、检索日期与工具版本、各检索式的原文与各来源实际发送的写法、各检索式 × 来源的命中数与保存数、去重与候选（规则次数）、本地匹配的偏差、文件。`report.py diff A B` 比较两份清单：检索结果文件的增减与变化（命中数、保存数、哈希）、候选的进出、配置是否相同。

`local_match` 只统计检索式由服务器执行的来源（OpenAlex、S2）：服务器返回的记录按定义满足检索式，其中有摘要、却被本地判为不满足的比例就是本地匹配漏判的上限。

### 6.5 `evidence/authors{suffix}.json`

```text
meta     source, script, input, merged, top, counts（from_search, looked_up, not_found）, retrieved_at, http
records  rank, merged_id, doi, openalex_id, openalex_title, title_matches, authors, n_authors, source, authors_from, error
```

阶段 4 起只在检索结果缺作者时才需要：`authors.py` 先读同目录的 `merged{suffix}.json`，候选已有作者的直接取用（`source: "search"`，`authors_from` 为原始记录的出处），只为缺作者的候选查 OpenAlex（`source: "openalex"`）。

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

- 只写与内置默认值不同的设置；`novelty-probe config show` 打印有效配置，`show --diff` 只打印改动，`check` 检查写法。
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
- `novelty-probe evidence check <表>` 机器检查：取值、标识符来自检索结果、题目 / 年份 / 作者与检索结果一致、引号内英文为摘要（或检索记录题目）原文；本篇无摘要时，判定依据中注明 DOI 的其他版本（在检索结果中）的摘要也算。两张教程证据表全部通过（Step 70–71）。
- JSON 形式（`evidence/evidence_table{suffix}.json`，schema `novelty-probe/evidence@1`）：`meta`（语言、面、取值、列、检索结果文件、对应的 Markdown、上次生成的 sha256）、`sections`（表外文字，原样保留）、`rows`（rank、merged_id、作者、年份、题目、doi、arxiv_id、各面取值、`verification` 结构化核验结果或 `verified_text`、判定依据）。从 Markdown 导入后再生成，与原文件逐字相同；换语言生成时只有表头与 verified 列（有结构化结果时）变化。教程的两张表仍以 Markdown 为准，没有提交 JSON。

### 6.7 `logs/RUN_LOG.md`

- **只追加**：新条目一律写在末尾，不改写已有条目。
- **条目格式**：以 `---` 分隔，标题写成 `## [YYYY-MM-DD HH:MM UTC] Step N — 标题`，正文包含研究者的要求、命令、输出、产出文件、备注。
- **编号**：下一步是 **Step 93**。命令加 `--log`、`novelty-probe run`、`novelty-probe logrun` 写的条目会自动接着编号；手写条目照旧接着日志里最后一个编号。
- **旧哈希**：Step 20 之前的条目里引用的是改写历史之前的提交哈希，按 Step 20 的对照表查新哈希。

## 7. 命令速查

命令写成 `novelty-probe <命令>`（未安装时 `python3 -m novelty_probe <命令>`，或旧入口 `python3 scripts/<命令>.py`，三者等价）。

| 命令 | 作用 | 常用参数 | 访问网络 | 退出码 |
|---|---|---|---|---|
| `init` | 新建项目目录（已有文件不覆盖；拒绝在源码仓库里新建） | `[目录]`、`--update-docs`、`--force` | 无 | 0；在源码仓库里或目标是文件时 2 |
| `run` | 一条命令跑完脚本步骤：check → search → qa → merge → authors（只在缺作者时）→ enrich；每一步写日志 | `--suffix`、`--queries`、`--from`、`--to`、`--enrich-top`、`--dry-run`、HTTP 参数 | 同各步骤 | 0 全部成功；否则为出错那一步的退出码；检索式文件不存在或参数错误时 2 |
| `search` | T3 检索（数据源取自注册表） | `--dry-run`、`--ids`、`--sources`、`--queries`、`--suffix` | api.openalex.org、api.semanticscholar.org（开启 Crossref 时还有 api.crossref.org） | 0 全部成功；1 有请求失败，或 dry-run 发现语法错误；2 检索式文件不合格或参数错误 |
| `qa` | 检索质量检查 | `--suffix` | 无 | 0 |
| `merge` | T4 合并去重、版本识别、RRF 排序、前 20 候选；同时写出 RIS、运行清单与检索报告 | `--suffix`、`--legacy` | 无 | 0 成功；没有记录或同一来源混有不同检索方式时报错退出 |
| `export` | 导出 RIS：候选（默认）、全部合并记录、证据表各行 | `--suffix`、`--all`、`--evidence`、`--results`、`--out` | 无 | 0 |
| `report` | 由运行清单生成检索报告；比较两份清单 | `render <清单> [--out]`、`diff <A> <B>` | 无 | 0 |
| `authors` | T5 补查作者（只查合并记录里缺作者的候选） | `--top`、`--candidates`、`--out` | api.openalex.org（有缺作者的候选时） | 0（单条失败记在 `error` 字段里） |
| `enrich` | T5 从其他版本补摘要 | `--top`、`--candidates`、`--out` | api.openalex.org | 0（单条失败记在 `error` 字段里） |
| `verify` | T5 DOI 核验 | `--table`、`--no-landing` | doi.org、api.crossref.org、api.openalex.org、出版商网站 | 0 元数据核验（Crossref 或 OpenAlex）全部成功；1 有失败 |
| `snowball` | T5b 引文追踪（一步 / 两步共被引） | `--from-evidence` 或 `--seeds`、`--cocite`、`--citer-filter`、`--min-support`、`--label`、`--suffix` | api.openalex.org | 0 |
| `compare` | 比较几轮结果、已知文献名次 | `--runs`、`--known`、`--ignore-phrases`、`--out` | 无 | 0 |
| `evidence` | 证据表：检查、Markdown 转 JSON、JSON 生成 Markdown | `check`、`import-md`、`render`；`--results`、`--authors`、`--enrichment`、`--out`、`--force` | 无 | check：0 没有问题，1 有问题；2 文件无法读取 |
| `config` | 查看与检查配置 | `show`、`show --diff`、`check`、`init` | 无 | 0；配置有误时 2；`init` 遇到已有文件时 1 |
| `logrun` | 运行任意命令并写日志（标题没有 Step 编号时自动接着编号） | `[--root 目录] "<步骤名>" -- <命令>` | 无 | 与被运行的命令相同；用法错误时为 1 |

任一命令加 `--log "<步骤名>"`（`run`、`logrun` 除外）：在子进程里运行这条命令，把命令与输出写进项目的 `logs/RUN_LOG.md`，退出码与命令相同。日志里的命令记成 `novelty-probe …`，不写本机的解释器路径。

所有命令都接受 `--root`（项目根目录；默认从当前目录向上找 `novelty-probe.json` 或 `PROJECT.md`，或环境变量 `NOVELTY_PROBE_ROOT`；都找不到时报错退出，不会落到工具的安装位置）、`--config`（或 `NOVELTY_PROBE_CONFIG`）、`--lang zh|en`（或 `NP_LANG`，或配置 `language`）。配置有误时以退出码 2 结束，并一次列出所有问题。`logrun.py` 用同样的规则确定项目根目录，并通过 `NOVELTY_PROBE_ROOT` 传给子进程。

所有联网的命令（search、authors、enrich、verify、snowball）共用 `novelty_probe/http.py` 的客户端，并接受同一组参数：`--http-mode live|cache|record|replay`（或环境变量 `NP_HTTP_MODE`）、`--cache-dir`（默认项目目录里的 `.cache/http`，已 gitignore）、`--cassette`（录制件路径）、`--refresh`。每个输出文件的 `meta.http` 记录请求数、缓存命中、重试、OpenAlex 额度头；`meta.warnings` 记录响应形状与解析核对的警告。S2 翻页与引文追踪的断点写在 `results/raw/.checkpoints/`，中断后重跑同一命令即续跑。

参数的默认值（都可在 `novelty-probe.json` 中修改，见 6.0）：

- 检索：`sources.openalex.top_n = 25`、`sources.semanticscholar.top_n = 25`、`sources.semanticscholar.max_records = 3000`、`queries.purposes.concurrent.year_from = 2023`、截断词表 `queries.truncation`；
- 合并：`merge.top_k = 20`、`merge.rrf_k = 60`、`merge.bm25 = {k1: 1.2, b: 0.75}`；版本识别 `versions.year_window = 3`、`versions.min_title_words = 5`、`versions.max_cluster_groups = 6`（一个合并组最多含几个标识符分组，超过即 R8）与预印本、数据集 DOI 前缀表（`--legacy` 不读配置，固定为前 20 篇、标题至少 5 个词）；
- 引文追踪：`snowball.min_overlap = 2`、`max_forward = 2000`、`top = 20`、`keep = 200`；相似度停用词 `textmatch.stopwords`；
- 比较：`compare.marker_terms`（默认词组 `genai`）；补摘要：`enrich.top = 20`；核验：`verify.landing = true`；
- HTTP：`novelty_probe/http.py` 的 `POLICIES`（按主机：最小间隔、最多尝试次数、退避基数与上限、Retry-After 上限 60 秒、熔断阈值、缓存 TTL、密钥环境变量名），可用 `http.policies` 按主机覆盖。

不可配置的：预印本版本规则 `PREPRINT_VERSION_RE`（`novelty_probe/record.py`）、去重规则的判断顺序与编号（`novelty_probe/dedupe.py`）、检索式 id 的 `Q<数字>` 格式（脚本之间的文件名约定）。

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
| GitHub Actions：Python 3.9–3.13 × Ubuntu / Windows，只跑离线测试与安装后的命令；~~macOS~~ 2026-11-03 起不再测试 | 研究者决定（决策点 4）；Windows 在云端测不了。macOS：节点排队常卡住、额度消耗快（研究者决定） | Step 69；Step 91 |
| User-Agent 默认是通用的客户端名，不带邮箱 | 助手不代填个人信息；研究者可以在配置里自己填 `contact_email` | Step 69 |
| `contact_email` 留空；教程的两张证据表保持 Markdown；进入阶段 3 | 研究者决定 | Step 73 |
| 保留受限的检索式语法（AND 连接 OR 组，尾部 NOT），解析一次成语法树，各数据源从同一棵树序列化 | 本地重排、`n_conform`、qa.py 都依赖这个形状；任意嵌套只会扩大出错面 | Step 66、80 |
| 以前放行的错误写法（未配对引号、逗号、缺 OR、缺 AND）改为报错 | 它们会让各来源检索到不同的内容；仓库里 72 个结果文件的检索式全部仍能解析 | Step 80 |
| OpenAlex 返回的解析树逐组核对：分组不同即报错不保存，结构不认识只警告 | 分组不同说明结果与意图不符；接口改了表示方式时不应误拦 | Step 80 |
| Crossref 适配器的本地判断从严：现有文字须满足整条检索式 | Crossref 不做布尔检索，标题不满足就无从证明；宁缺毋滥 | Step 76、80 |
| 减少中间环节的人工参与：不设去重复核表；作者随检索取得；RIS、运行清单与检索报告在合并时自动写出 | 研究者决定（文献探查只是研究的起点） | Step 81 |
| CI 不加 Python 3.14；Crossref 保持默认关闭；导出格式只做 RIS | 研究者决定 | Step 81 |
| 去重的每个决定记规则编号（D1–D5 合并，R1–R8 保持分开）；作者作证据：同题但两边作者名没有一个相同时不并（R7），题目几乎相同且有共同作者时才并（D5）；一方的作者名不可比（如只用汉字书写）时作者不作证据 | 证据不足时宁可不并（与阶段 3 相同的取向）；作者是题目之外最可靠的证据；规则编号让每个决定可追溯 | Step 81、87 |
| 合并组最多含 6 个标识符分组（R8） | 防止通过标题连锁误并；v1、v2、v1b、v2b 中最大的合并组都是 2 个分组 | Step 87 |
| 检索报告的格式参照 PRISMA-S；运行清单记输入输出的哈希 | 方法部分需要可复现、可核对的检索记录 | Step 87 |
| 发布 v2.0.0：面向实际研究使用；加一条命令跑完脚本步骤；不发布到 PyPI | 研究者决定 | Step 88 |
| 各命令移入包内（`novelty_probe/commands/`），`scripts/*.py` 保留为转发的入口；输出与 1.x 逐字节相同（`meta.script` 等取值不变） | 可安装才能在仓库之外使用；日志与笔记里的旧命令要能照常重跑 | Step 88–90 |
| 每个想法一个项目目录（`novelty-probe init`），默认拒绝建在源码仓库里 | 研究想法与结果属于研究者，不应混进公开的工具仓库；工具升级不碰研究数据 | Step 90 |
| 仓库根目录的 `PROJECT.md`、`AGENTS.md`、`HOWTO.md` 与新项目的模板相同（测试保证） | 教程示例与新项目遵守同一套规则；改一处时测试提醒同步另一处 | Step 90 |
| 运行日志的 Step 编号由命令自动接着编（`run`、`--log`、`logrun`）；日志里的命令记成 `novelty-probe …`，不写本机的解释器路径 | 编号格式与手写条目一致，减少手工；本机路径可能含用户名 | Step 90 |
| 安装后的包找不到项目目录时报错，不落到安装位置；HTTP 缓存默认放在项目目录 | 不往 site-packages 里写结果与缓存 | Step 90 |
| 隐私：录制件在录制时去掉响应里的电子邮件地址；运行日志把用户目录记成 `~`；运行日志概括研究者的决定，不逐字引用对话原文；测试检查仓库里没有电子邮件地址 | 仓库公开，研究者要求发布前检查隐私 | Step 91 |
| 数据条款：检索报告列出各数据源的条款与署名（Semantic Scholar 按其许可协议要求链接回去）；README 说明仓库里第三方数据的来源、条款与撤除渠道；`init` 的 `.gitignore` 说明公开项目时如何不提交第三方数据 | Semantic Scholar 的 API 许可协议要求公开使用时署名并链接回去，并限制把数据转给第三方；摘要的版权属于出版方或作者 | Step 91 |
| 保留仓库里已有的第三方数据（署名、条款与撤除渠道见 README，发布的压缩包不含这些数据）；不改写提交历史；仓库不改名 | 研究者决定 | Step 92 |

## 9. 已知问题与可改进处

第 9 节原来列出的十个问题已按 `docs/IMPROVEMENT_PLAN.md` 处理（Step 24–64），评估见该文件第 12 节；两张证据表的核验列已用改进后的 `verify.py` 刷新（Step 62–63）。仍需注意：

1. **召回仍依赖人的判断**：v1 的检索式本身检索不到参考文献；两步共被引能把它排到第 1，但只在引用者按情境词（scientists）过滤时如此，换用其他面的词就找不到，而且这一过滤方式是调研时在知道目标的情况下试出的。v2b 的情境（经济学与管理学研究者）中通过过滤的引用者只有 2 篇，共被引几乎没有信息。
2. **剩余噪声**：v2b 前 20 中仍有 1 篇只因 "narrow applications" 命中 narrowing；NOT 短语是看过结果后定的。是否采用 NOT、如何处理剩余用法，由研究者决定（v2b 只是演示，`queries/queries_v2.json` 未改动）。
3. **版本识别以标题为主**：阶段 4 起作者作为证据（同题无共同作者不并；题目几乎相同且有共同作者才并），但标题改动较大的预印本与正式版仍不会合并；阶段 4 之前检索的结果没有作者，只按标题与原有检查。
4. **检索式设计决定排序上限**：v1b 前 20 中仍有通用的文献计量综述和一篇 1993 年的药物设计论文，来自宽泛的方法类检索式和只有 8–9 条命中的 Q3；v2b 前 10 中有 3 篇来自不含 AI 词组的 Q2 的早年文献。
5. **无摘要的记录**：按题目找不到带摘要的其他版本时，仍只能靠题目标注（v1b、v2b 前 20 中各 3 篇）。
6. **落地页核验**：云端被网络策略拦截；本地出版商常对脚本返回 403（可用 `--no-landing` 只核验元数据）。
7. **质量检查是近似**：`qa.py` 用 Porter 词干还原近似两个 API 的匹配（API 更像 KStem）。偏差已可量化：服务器按布尔检索式返回、有摘要、却被本地判为不满足的比例，v1b 为 OpenAlex 1.1%（87 条中 1 条）、S2 6.4%（94 条中 6 条），`qa.py` 与检索报告每次都会给出（Step 87）。
8. **OpenAlex 额度**：云端注入的 key 有每日 1 美元的上限，且可能与其他任务共用；带检索条件的请求每次 0.001 美元。
8a. **S2 的 429**：云端的 S2 key 已确认生效（只有带有效 key 才能访问的数据集接口返回 200），但请求间隔 2 秒时仍有约一半返回 429（Step 65），像是这个 key 的额度同时被别处占用。`search.py` 会按 2、4、8… 秒退避重试，最终成功，只是更慢。
9. **证据检查的边界**：`evidence.py check` 按词序比对引文（大小写、标点不计），能抓出改写和编造的引文，但不判断标注是否合理；中文引号内的转述不检查；作者与合并记录（检索时取得）或 `authors*.json` 比对，与任一处一致即可，两处都没有作者时不比对。
10. **Crossref 检索源**（决策点 2：实现但默认关闭，阶段 3 已实现）：它的检索面向参考文献匹配，实测教程的长检索式在前 40 条里没有满足检索式的记录（Step 75–77），两三个词的简单检索式效果好得多（Step 78）。
10a. **OpenAlex 对未加引号的连字符词**：示例检索式里没有这种写法，OpenAlex 怎样解析未经实测；dry-run 会提示加引号，分组核对若发现 OpenAlex 拆开了它，会报错不保存。
11. **待研究者确认**：v2 证据表 rank 8 的"研究问题"面按研究者标准改为 overlap 是助手的推断（Step 25）；v1b、v2b 没有证据表，是否以它们替代 v1、v2 由研究者决定。
12. **Python 3.9 已过官方支持期**（2025-10）：本工具仍支持并在 CI 中测试 3.9；以后若要用 3.10 才有的写法，再一并停用 3.9。
12a. **仓库里的第三方数据**（研究者决定保留，Step 92）：`results/`、`examples/tutorial/results/`、`evidence/enrichment*.json` 与 `tests/fixtures/cassettes/` 里有 Semantic Scholar 的数据与各来源的摘要。处理方式：README 写明署名、条款与撤除渠道；发布的压缩包不含这些数据（Step 91）。有权利人提出要求时再移除，并改用合成数据。
13. **仓库名**：保持 `novelty-probe-demo`，不改名（研究者决定，Step 92）。

## 10. Git 与发布

- **工作流**：在新分支上修改 → 推送 → 开 PR → 合并 → 删除分支。建议在仓库 Settings 里开启 "Automatically delete head branches"。
- **`main` 规则集**：禁止删除、禁止强推、必须走 PR（审批人数 0，bypass 为空）。
- **提交约定**：提交信息不放会话链接或个人信息；作者邮箱用 GitHub 的 noreply 地址。
- **发布新版本**：版本号只写在两处，`novelty_probe/__init__.py` 的 `__version__`（`pyproject.toml` 由它取）与 `CITATION.cff` 的 `version`（测试检查两者一致）；同时改 `date-released` 与 `CHANGELOG.md`。PR 合并后在 GitHub 上 Releases → Draft a new release：新建标签 `v<版本>`（目标 `main`），标题 `novelty-probe v<版本>`，说明取自 `CHANGELOG.md` 的对应一节，Publish。HOWTO 与 README 里的安装地址 `…/archive/refs/tags/v<版本>.zip` 在标签建好后才可用。压缩包只含工具本身：教程示例的数据（含第三方数据与摘要）、测试件与运行日志在 `.gitattributes` 里标为 `export-ignore`，不打进 Release 与 Download ZIP（仍在仓库里）。发布日期与 `date-released` 不同时，随后改一下 `CITATION.cff`。如果开通了 Zenodo，它会自动存档并分配 DOI。
- **v2.0.0**：已于 2026-11-03 发布（标签 `v2.0.0` → 5c0ed59，说明取自 `CHANGELOG.md` 的 2.0.0 一节）。发布页面上目前标为 pre-release，所以仓库首页的 "Latest" 仍显示 v1.0.0；要改为正式版，在 Release 的编辑页取消 "Set as a pre-release"，并勾选 "Set as the latest release"。安装地址不受影响。
- **不要提交 API key**。`.gitignore` 已忽略 `__pycache__/`。

## 11. 交接检查清单

- [ ] 按第 3 节建虚拟环境、升级 pip 与 setuptools，从克隆安装；`novelty-probe --version` 显示 2.0.0
- [ ] 设置 `OPENALEX_API_KEY`（可选 `S2_API_KEY`），重开 ZCode 后用 3.6 的命令核对（只看是否已设置）
- [ ] `python -m unittest discover -s tests -v` 显示 `OK (skipped=6)`
- [ ] 3.9 的不联网冒烟测试通过，并删除临时目录
- [ ] 在 ZCode 中让 GLM 读完 `AGENTS.md`、`PROJECT.md`、`HOWTO.md`、`HANDOFF.md`，并复述三条硬规则（第 4 节的第一条消息）
- [ ] 开始新想法时，用 `novelty-probe init` 在仓库之外新建项目目录（`HOWTO.md` 第 1 节），不要动仓库里的示例产出
