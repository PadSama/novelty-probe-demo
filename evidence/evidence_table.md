# 证据表：前 10 篇候选

> 本表只记录每篇文献在各个面上与想法的对应关系，不判断新颖性（PROJECT.md 规则 a）。

**来源**

- 文献：`results/merged/candidates.csv` 前 10 篇。该文件按命中次数排序（见 `logs/RUN_LOG.md` Step 6），排序反映两个来源是否都检索到，**不代表与研究问题的相关度**，所以这 10 篇只说明它们自身的情况。
- 年份：各版本中最早的年份（预印本早于正式发表时取预印本年份）。
- 作者：按 DOI 从 OpenAlex 查询（`scripts/authors.py` → `evidence/authors.json`），超过 3 位作者时只列前 3 位。
- verified 列：由 `scripts/verify.py` 写入（请求 `https://doi.org/<DOI>` 并跟随跳转，记录 HTTP 状态与返回页标题）。

**标注规则**（只依据摘要；没有摘要时，只在题目足以判断的面上标注，其余标 unknown）

- **overlap**：在这一面上与本想法相同或高度相近
- **differ**：摘要明确显示在这一面上不同（对象、情境、方法或结论不同），或该文不涉及这一面的内容
- **unknown**：摘要信息不足以判断

| 面 | 本想法（facets/facets.md） | 记 overlap 的条件 |
|---|---|---|
| 研究问题 | 科研人员使用 AI 工具，学科层面的选题范围是否收窄 | 研究 AI 使用对科研选题或研究方向的范围、多样性的影响 |
| 作用机制 | 同质化、算法单一化、路灯效应、探索–利用、马太效应 | 摘要提出或检验了其中一种机制 |
| 研究情境 | 科研人员使用生成式 AI（2022 年底以后） | 科研情境，且涉及生成式 AI 工具的使用；只满足其一记 differ |
| 数据与方法 | 大规模论文数据：测 AI 使用、测选题范围、因果识别 | 用论文数据做文献计量或主题分析 |
| 预期发现 | 选题范围收窄、多样性下降 | 报告了范围收窄或多样性下降；报告变宽（多样化）或与多样性无关的结论记 differ |

## 表

| rank | 作者 | 年份 | 题目 | DOI/arXiv | 研究问题 | 作用机制 | 研究情境 | 数据与方法 | 预期发现 | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Zhen Zhang; Zhichu Ren; Chia-Wei Hsu et al. | 2025 | A multimodal robotic platform for multi-element electrocatalyst discovery | doi:10.1038/s41586-025-09640-5 | differ | unknown | unknown | differ | unknown | BLOCKED at doi.org (network policy, proxy 403) |
| 2 | Anil Rajnikant Doshi; Oliver Hauser | 2023 | Generative AI enhances individual creativity but reduces the collective diversity of novel content | doi:10.1126/sciadv.adn5290 · arXiv:2312.00506 | differ | overlap | differ | differ | overlap | BLOCKED at doi.org (network policy, proxy 403) |
| 3 | Stuart R. Borrett; Laura Sheble; James W. Moody et al. | 2018 | Bibliometric review of ecological network analysis: 2010–2016 | doi:10.1016/j.ecolmodel.2018.04.020 | differ | differ | differ | overlap | differ | BLOCKED at doi.org (network policy, proxy 403) |
| 4 | Barrett R. Anderson; Jash Hemant Shah; Max Kreminski | 2024 | Homogenization Effects of Large Language Models on Human Creative Ideation | doi:10.1145/3635636.3656204 · arXiv:2402.01536 | differ | overlap | differ | differ | overlap | BLOCKED at doi.org (network policy, proxy 403) |
| 5 | Hanadi Aldreabi; Mohammad Alhur; Manaf Al‐Okaily et al. | 2025 | Unveiling the dynamics of generative AI adoption: A business intelligence analysis through topic modeling-based bibliometric study | doi:10.1016/j.caeai.2025.100456 | differ | differ | differ | overlap | differ | BLOCKED at doi.org (network policy, proxy 403) |
| 6 | Kumari Rashmi; Aakanksha Kataria | 2021 | Work–life balance: a systematic literature review and bibliometric analysis | doi:10.1108/ijssp-06-2021-0145 | differ | differ | differ | overlap | differ | BLOCKED at doi.org (network policy, proxy 403) |
| 7 | Payal R. Phulwani; Divesh Kumar; Praveen Goyal | 2020 | A Systematic Literature Review and Bibliometric Analysis of Recycling Behavior | doi:10.1080/08911762.2020.1765444 | differ | differ | differ | overlap | differ | BLOCKED at doi.org (network policy, proxy 403) |
| 8 | Ross D. King; Ashwin Srinivasan; Stephen Muggleton et al. | 1993 | Drug design using inductive logic programming | doi:10.1109/hicss.1993.270676 | differ | differ | differ | differ | differ | BLOCKED at doi.org (network policy, proxy 403) |
| 9 | Xueqi Yin | 2026 | A temporal adaptive dictionary-constrained LDA and Bi-calibrated dual granularity DTM framework for dynamic topic evolution analysis in academic papers | doi:10.1038/s41598-026-54348-9 | differ | differ | differ | overlap | differ | BLOCKED at doi.org (network policy, proxy 403) |
| 10 | T. Orchard; Leszek Tasiemski | 2023 | The rise of generative AI and possible effects on the economy | doi:10.18559/ebr.2023.2.732 | differ | differ | differ | differ | differ | BLOCKED at doi.org (network policy, proxy 403) |

## 判定依据

引号内为摘要原文。

**1 · M010**（本地记录无摘要）
- 两个来源都没有返回摘要。两个来源都是按"标题 + 摘要"命中 Q4 的，说明其摘要含 Q4 的检索词，但无法在本地核对。
- 研究问题 differ、数据与方法 differ：依据题目，该文提出一个用于电催化剂发现的多模态机器人平台，不研究科研选题范围，也不使用论文数据。
- 作用机制、研究情境、预期发现 unknown：仅凭题目无法判断。

**2 · M031**
- 研究问题 differ：研究 "the causal impact of generative AI ideas on the production of short stories"，对象是故事内容，不是科研选题。关系结构相近：个人使用生成式 AI，看集体层面的多样性。
- 作用机制 overlap："generative AI-enabled stories are more similar to each other than stories by humans alone"，并提到 "anchoring on generative AI ideas"（同质化）。
- 研究情境 differ：写作者使用 LLM 提供的故事创意，不是科研人员；工具是生成式 AI。
- 数据与方法 differ："an online experiment"。
- 预期发现 overlap："collectively a narrower scope of novel content is produced"（集体层面范围收窄；对象是故事）。

**3 · M039**
- 研究问题 differ：系统回顾生态网络分析（ENA）领域的主题、方法与合作，不涉及 AI。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：学术文献情境，但不涉及 AI。
- 数据与方法 overlap："a combination of bibliometric, network (e.g., social network), and feature analyses"；"A topic network built from the bibliographic records"。样本仅 186 条。
- 预期发现 differ：结论是该领域 "a topically diverse and collaborative science domain"，是静态描述，不涉及收窄。

**4 · M024**
- 研究问题 differ：研究 LLM 作为创意支持工具对用户创意构思的影响，对象不是科研选题。
- 作用机制 overlap：明确检验同质化假设，结果 "in accordance with the homogenization hypothesis"。
- 研究情境 differ："a 36-participant comparative user study"，使用 ChatGPT；摘要未说明参与者是科研人员，任务是创意构思。
- 数据与方法 differ：对照用户研究。
- 预期发现 overlap："different users tended to produce less semantically distinct ideas with ChatGPT"（用户之间的多样性下降）。

**5 · M022**
- 研究问题 differ：梳理"生成式 AI 在教育中"这一文献的主要主题，不研究 AI 使用对选题范围的影响。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：生成式 AI 是被分析文献的主题，不是科研人员使用的工具。
- 数据与方法 overlap："bibliometric analysis and topic modeling focusing on the R program's structural topic model (STM) Package"。
- 预期发现 differ：结论是 "nine pivotal topics" 与合作网络，"Lotka's Law suggests that the field is still in its early stages"，不涉及收窄。

**6 · M035**
- 研究问题 differ：梳理工作–生活平衡研究的动态，不涉及 AI。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：不涉及 AI。
- 数据与方法 overlap："Scopus database ... based on 945 research papers"，文献耦合聚类。
- 预期发现 differ：报告该领域的 "research diversification"（多样化，方向与预期相反，且与 AI 无关）。本文由 Q2 的反向词命中。

**7 · M036**
- 研究问题 differ：梳理回收行为研究的发展，不涉及 AI。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：不涉及 AI。
- 数据与方法 overlap："The 788 articles ... were analyzed"，引文分析与文献耦合。
- 预期发现 differ："the research had diversified into seven identifiable clusters"（多样化，与 AI 无关）。本文由 Q2 的反向词命中。

**8 · M042**
- 研究问题 differ：用归纳逻辑编程（ILP）做药物设计中的定量构效关系分析。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：1993 年的机器学习应用，不属于研究者限定的生成式 AI。
- 数据与方法 differ：机器学习方法的应用，不使用论文数据。
- 预期发现 differ：结论是一套方法流程，不涉及多样性。
- 备注：摘要中 "identification of the problem, choice of a representation" 去掉标点后构成短语 "problem choice"，这可能是它被 Q3 命中的原因。

**9 · M002**
- 研究问题 differ：提出主题演化模型并分析 AI 领域论文的主题变化；"research topic selection" 只出现在研究动机中。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：AI 是被分析的学科，不是科研人员使用的工具。
- 数据与方法 overlap："English AI papers retrieved from the Web of Science (WOS) Core Collection (2014-2023)"，用 LDA 与动态主题模型追踪主题强度和主题关联的变化。
- 预期发现 differ：报告 AI 领域内主题此消彼长（"generative AI", "large language models", and "multimodal learning" evolving into explosive topics after 2021, traditional machine learning shows a declining trend），不涉及 AI 使用导致的收窄。

**10 · M032**
- 研究问题 differ：分析生成式 AI 对商业与经济的可能影响。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：商业与经济，不是科研人员。
- 数据与方法 differ：情景讨论，摘要未报告数据。
- 预期发现 differ：讨论岗位替代、新岗位与网络犯罪风险，不涉及多样性。
