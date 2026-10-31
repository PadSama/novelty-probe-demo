# 证据表 v2：前 10 篇候选

> 本表只记录每篇文献在各个面上与想法（`idea/idea_v2.md`）的对应关系，不判断新颖性（PROJECT.md 规则 a）。

**来源**

- 文献：`results/merged/candidates_v2.csv` 前 10 篇（按命中次数排序，见 `logs/RUN_LOG.md` Step 14）。排序反映两个来源是否都检索到，**不代表与研究问题的相关度**，所以这 10 篇只说明它们自身的情况。
- 年份：各版本中最早的年份。
- 作者：按 DOI 从 OpenAlex 查询（`scripts/authors.py` → `evidence/authors_v2.json`），超过 3 位作者时只列前 3 位。
- verified 列：由 `scripts/verify.py` 写入，格式为"Crossref 结果；落地页结果"。两项检查都从 `https://doi.org/<DOI>` 出发并跟随跳转：Crossref 一项取登记的元数据，并把登记题目与表中题目对照；落地页一项记录出版商页面的 HTTP 状态与页面标题。BLOCKED 表示本环境的网络策略不允许访问该域名。

**标注规则**（只依据摘要；没有摘要时，只在题目足以判断的面上标注，其余标 unknown）

- **overlap**：在这一面上与本想法相同或高度相近
- **differ**：摘要明确显示在这一面上不同（对象、情境、方法或结论不同），或该文不涉及这一面的内容
- **unknown**：摘要信息不足以判断

| 面 | 本想法（facets/facets_v2.md） | 记 overlap 的条件 |
|---|---|---|
| 研究问题 | 研究者使用 AI 工具，学科层面的选题范围是否收窄 | 研究 AI 使用对科研选题或研究方向的范围、多样性的影响（不限学科，学科差异记在研究情境） |
| 作用机制 | 同质化、算法单一化、路灯效应、探索–利用、马太效应 | 摘要提出或检验了其中一种机制 |
| 研究情境 | 管理学与经济学研究者使用生成式 AI（2022 年底以后） | 管理学或经济学的研究情境，且涉及生成式 AI 工具的使用；只满足其一记 differ |
| 数据与方法 | 大规模论文数据：测 AI 使用、测选题范围、因果识别 | 用论文数据做文献计量或主题分析 |
| 预期发现 | 选题范围收窄、多样性下降 | 报告了范围收窄或多样性下降；报告变宽或与多样性无关的结论记 differ |

## 表

| rank | 作者 | 年份 | 题目 | DOI/arXiv | 研究问题 | 作用机制 | 研究情境 | 数据与方法 | 预期发现 | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Wim A. Naudé | 2023 | Artificial Intelligence and the Economics of Decision-Making | doi:10.2139/ssrn.4389118 | differ | differ | differ | differ | differ | Crossref HTTP 200 · 题目一致 · Artificial Intelligence and the Economics of Decision-Making；落地页 BLOCKED at www.ssrn.com (network policy, proxy 403) |
| 2 | Anil Rajnikant Doshi; Oliver Hauser | 2023 | Generative AI enhances individual creativity but reduces the collective diversity of novel content | doi:10.1126/sciadv.adn5290 · arXiv:2312.00506 | differ | overlap | differ | differ | overlap | Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the collective diversity of novel content；落地页 BLOCKED at www.science.org (network policy, proxy 403) |
| 3 | Qianyue Hao; Fengli Xu; Yong Li et al. | 2026 | Artificial intelligence tools expand scientists’ impact but contract science’s focus | doi:10.1038/s41586-025-09922-y | overlap | overlap | differ | overlap | overlap | Crossref HTTP 200 · 题目一致 · Artificial intelligence tools expand scientists’ impact but contract science’s focus；落地页 BLOCKED at www.nature.com (network policy, proxy 403) |
| 4 | Barrett R. Anderson; Jash Hemant Shah; Max Kreminski | 2024 | Homogenization Effects of Large Language Models on Human Creative Ideation | doi:10.1145/3635636.3656204 · arXiv:2402.01536 | differ | overlap | differ | differ | overlap | Crossref HTTP 200 · 题目一致 · Homogenization Effects of Large Language Models on Human Creative Ideation；落地页 BLOCKED at dl.acm.org (network policy, proxy 403) |
| 5 | Hanadi Aldreabi; Mohammad Alhur; Manaf Al‐Okaily et al. | 2025 | Unveiling the dynamics of generative AI adoption: A business intelligence analysis through topic modeling-based bibliometric study | doi:10.1016/j.caeai.2025.100456 | differ | differ | differ | overlap | differ | Crossref HTTP 200 · 题目一致 · Unveiling the dynamics of generative AI adoption: A business intelligence analysis through topic modeling-based bibliome…；落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403) |
| 6 | Andreas Martin Jungherr | 2023 | Artificial Intelligence and Democracy: A Conceptual Framework | doi:10.1177/20563051231186353 | differ | differ | differ | differ | differ | Crossref HTTP 200 · 题目一致 · Artificial Intelligence and Democracy: A Conceptual Framework；落地页 BLOCKED at journals.sagepub.com (network policy, proxy 403) |
| 7 | Ильдар Узбекович Зулькарнай | 2025 | Issues of using artificial intelligence in scientific research of socio-economic processes | doi:10.47309/2713-2358-2025-4-184-195 | differ | differ | overlap | differ | differ | Crossref HTTP 200 · 题目一致 · Issues of using artificial intelligence in scientific research of socio-economic processes；落地页 BLOCKED at elibrary.ru (network policy, proxy 403) |
| 8 | Zhivar Sourati; Alireza S. Ziabari; Morteza Dehghani | 2025 | The homogenizing effect of large language models on human expression and thought | doi:10.1016/j.tics.2026.01.003 · arXiv:2508.01491 | differ | overlap | differ | differ | overlap | Crossref HTTP 200 · 题目一致 · The homogenizing effect of large language models on human expression and thought；落地页 BLOCKED at linkinghub.elsevier.com (network policy, proxy 403) |
| 9 | Meina Zhu; Lei Xu; Barbara Jane Ericson | 2025 | A systematic review of research on large language models for computer programming education | doi:10.48550/arxiv.2506.21818 · arXiv:2506.21818 | differ | differ | differ | overlap | differ | Crossref BLOCKED at data.crosscite.org (network policy, proxy 403)；落地页 BLOCKED at arxiv.org (network policy, proxy 403) |
| 10 | Ramesh Paudyal; Akash Deelip Shah; Oğuz Akın et al. | 2023 | Artificial Intelligence in CT and MR Imaging for Oncological Applications | doi:10.3390/cancers15092573 | differ | differ | differ | differ | differ | Crossref HTTP 200 · 题目一致 · Artificial Intelligence in CT and MR Imaging for Oncological Applications；落地页 BLOCKED at www.mdpi.com (network policy, proxy 403) |

## 判定依据

引号内为摘要原文。

**检索噪声提示**：rank 1、6、7、10 的标题和摘要里，与"选题收窄"有关的检索词只有词干还原后的 narrow，出现在 "narrow applications"、"narrow artificial intelligence"、"narrow systems of AI"、"narrow-specific tasks" 中，指的是专用、窄任务的 AI，与选题收窄无关。这是 v2 把 "narrowing of science" 放宽为 narrowing 带来的噪声（核对见 `logs/RUN_LOG.md` Step 15）。

**1 · M001**
- 研究问题 differ：讨论微观经济学的决策理论（期望效用理论）如何帮助 AI 科学家构建理性智能体，不研究 AI 使用对选题的影响。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：涉及经济学（"economic decision theory"，"economists may learn from AI scientists"），但不是研究者使用生成式 AI 工具。
- 数据与方法 differ：概念性的章节，不使用论文数据。
- 预期发现 differ："using EUT restricts AI systems to narrow applications"，指 AI 系统的适用范围，不是选题收窄。

**2 · M027**（同 v1 证据表 rank 2）
- 研究问题 differ：研究 "the causal impact of generative AI ideas on the production of short stories"，对象是故事内容，不是科研选题。
- 作用机制 overlap："generative AI-enabled stories are more similar to each other than stories by humans alone"，并提到 "anchoring on generative AI ideas"（同质化）。
- 研究情境 differ：写作者使用 LLM 提供的故事创意，不是管理学或经济学研究者。
- 数据与方法 differ："an online experiment"。
- 预期发现 overlap："collectively a narrower scope of novel content is produced"（集体层面范围收窄；对象是故事）。

**3 · M003**（本地记录无摘要；依据同一研究的 arXiv 预印本摘要）
- 两个来源都没有返回 Nature 版的摘要。v2 结果中有同一研究的 arXiv 预印本（M106，doi:10.48550/arxiv.2412.07727，题目相同，另带 "(Just accepted by Nature, to be online soon)"），以下引文出自预印本摘要，与正式版的文字可能有出入。合并时两条没有并成一篇，因为预印本题目多了这段后缀，两条记录之间也没有共同的 DOI 或 arXiv ID。
- 研究问题 overlap："AI adoption shrinks the collective volume of scientific topics studied by 4.63%"，研究 AI 使用对科学选题范围的影响。
- 作用机制 overlap："AI-augmented work moves collectively toward areas richest in data"（对应路灯效应）；"AI tools appear to automate established fields rather than explore new ones"（对应探索–利用）。
- 研究情境 differ："41.3 million research papers across natural science"，是自然科学而非管理学或经济学；AI 指各个时期的 AI 工具（"covering distinct eras of AI"），不限于生成式 AI。研究者另告知：该论文明确排除了经济学和商科（摘要中未提及，本表未能核对）。
- 数据与方法 overlap："we used a pretrained language model to identify AI-augmented research"；"a dataset of 41.3 million research papers"（大规模论文数据，加上测 AI 使用）。
- 预期发现 overlap："a collective narrowing of scientific focus"；"a contraction in collective science's reach"。

**4 · M021**（同 v1 证据表 rank 4）
- 研究问题 differ：研究 LLM 作为创意支持工具对用户创意构思的影响，对象不是科研选题。
- 作用机制 overlap：结果 "in accordance with the homogenization hypothesis"。
- 研究情境 differ："a 36-participant comparative user study"，使用 ChatGPT，任务是创意构思，摘要未说明参与者是研究者。
- 数据与方法 differ：对照用户研究。
- 预期发现 overlap："different users tended to produce less semantically distinct ideas with ChatGPT"。

**5 · M018**（同 v1 证据表 rank 5）
- 研究问题 differ：梳理生成式 AI 在教育领域的文献的主要主题。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：被分析的是教育文献，生成式 AI 是文献主题，不是管理学或经济学研究者使用的工具。
- 数据与方法 overlap："bibliometric analysis and topic modeling focusing on the R program's structural topic model (STM) Package"。
- 预期发现 differ：结论是 "nine pivotal topics" 与合作网络，不涉及收窄。

**6 · M025**
- 研究问题 differ：提出分析 AI 对民主影响的概念框架。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：政治与民主领域，不是管理学或经济学研究者使用生成式 AI。
- 数据与方法 differ：概念框架，不使用论文数据。
- 预期发现 differ："narrow artificial intelligence focused on solving specific tasks" 指专用 AI，不是选题收窄。

**7 · M015**
- 研究问题 differ：讨论 AI 在社会经济研究中的用处与障碍（"AI hallucinations" 等），不研究 AI 使用对选题范围的影响。
- 作用机制 differ：不涉及上述机制。
- 研究情境 overlap："scientific research of socio-economic processes"（经济学研究情境），并讨论 "existing AI systems, such as Yandex's Alice and ChatGPT"（生成式 AI 工具）。
- 数据与方法 differ：论述性文章，不使用论文数据。
- 预期发现 differ：结论是需要开发 "specialized, so-called narrow systems of AI"，指专用 AI，不是选题收窄。

**8 · M016**
- 研究问题 differ：研究 LLM 对人类表达与思维多样性的影响，对象不是科研选题。
- 作用机制 overlap："amplifying convergence as all people increasingly rely on the same models across contexts"（同质化、算法单一化）。
- 研究情境 differ：一般人群，不是管理学或经济学研究者。
- 数据与方法 differ：跨学科证据综述（"We synthesize evidence across linguistics, psychology, cognitive science, and computer science"），不分析论文数据。
- 预期发现 overlap："they risk standardizing language and reasoning"；"this homogenization risks flattening the cognitive landscapes"（多样性下降，属综述性结论；对象是语言与思维）。

**9 · M012**
- 研究问题 differ：系统综述 LLM 在编程教育中的研究。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：编程教育，LLM 是被综述的主题。
- 数据与方法 overlap："42 studies ... were reviewed using methods, including bibliometric analysis, thematic analysis, and structural topic modeling"（样本仅 42 篇）。
- 预期发现 differ：提出 "the need to expand research methods and topics"，是建议而非收窄的发现。

**10 · M026**
- 研究问题 differ：综述 AI 在肿瘤 CT 与 MR 影像中的应用。
- 作用机制 differ：不涉及上述机制。
- 研究情境 differ：临床肿瘤影像，不是管理学或经济学研究；AI 不限于生成式 AI。
- 数据与方法 differ：叙述性综述，不分析论文数据。
- 预期发现 differ："new AI tools for narrow-specific tasks" 指窄任务 AI，不是选题收窄。
