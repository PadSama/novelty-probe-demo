# 差异陈述

> 第 1 节由文献检索助手按下方规则从证据表复制；第 2、3 节由研究者填写。本文件不判断新颖性（PROJECT.md 规则 a）。
> 想法见 `idea/idea.md`，各面定义见 `facets/facets.md`，文献与标注见 `evidence/evidence_table.md`。

## 1. 最接近的三篇（从证据表复制）

从 `evidence/evidence_table.md` 原样复制整行（rank 2、4、9），选择规则见表下。

| rank | 作者 | 年份 | 题目 | DOI/arXiv | 研究问题 | 作用机制 | 研究情境 | 数据与方法 | 预期发现 | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | Anil Rajnikant Doshi; Oliver Hauser | 2023 | Generative AI enhances individual creativity but reduces the collective diversity of novel content | doi:10.1126/sciadv.adn5290 · arXiv:2312.00506 | differ | overlap | differ | differ | overlap | Crossref HTTP 200 · 题目一致 · Generative AI enhances individual creativity but reduces the collective diversity of novel content；落地页 BLOCKED at www.science.org (network policy, proxy 403) |
| 4 | Barrett R. Anderson; Jash Hemant Shah; Max Kreminski | 2024 | Homogenization Effects of Large Language Models on Human Creative Ideation | doi:10.1145/3635636.3656204 · arXiv:2402.01536 | differ | overlap | differ | differ | overlap | Crossref HTTP 200 · 题目一致 · Homogenization Effects of Large Language Models on Human Creative Ideation；落地页 BLOCKED at dl.acm.org (network policy, proxy 403) |
| 9 | Xueqi Yin | 2026 | A temporal adaptive dictionary-constrained LDA and Bi-calibrated dual granularity DTM framework for dynamic topic evolution analysis in academic papers | doi:10.1038/s41598-026-54348-9 | differ | differ | differ | overlap | differ | Crossref HTTP 200 · 题目一致 · A temporal adaptive dictionary-constrained LDA and Bi-calibrated dual granularity DTM framework for dynamic topic evolut…；落地页 BLOCKED at www.nature.com (network policy, proxy 403) |

**选择规则**（只依据证据表的标注与摘要；"最接近"只表示在证据表中的相对位置，不是对新颖性的判断）

1. 按标为 overlap 的面数排序：rank 2、rank 4 各有 2 个面 overlap（作用机制、预期发现），其余各篇至多 1 个，二者入选。
2. 第三篇从 5 篇并列中选出（rank 3、5、6、7、9，均只在"数据与方法"面 overlap）：
   - 先保留标题或摘要涉及生成式 AI 的论文（研究者确定的范围与筛选关键词：LLM、ChatGPT、Gemini、Claude、OpenAI、Anthropic 等），剩 rank 5 与 rank 9；
   - 再比较"数据与方法"面覆盖 facets.md 所列内容的多少：rank 9 的摘要写明数据为 Web of Science 2014–2023 年的英文 AI 论文，并用动态主题模型追踪主题随时间的变化（学科级、跨年份的论文数据，加上测选题范围）；rank 5 的摘要只报告主题归纳，未说明数据规模与时间跨度（只对应测选题范围）。取 rank 9。

## 2. 本想法在哪一个面上不同、差多大（人填）

- 面（研究问题 / 作用机制 / 研究情境 / 数据与方法 / 预期发现）：
- 不同之处：
  - rank 2、rank 4 研究的是同一个机制：个人借助生成式 AI 得益，集体层面的多样性却下降。但对象是短篇故事写作和创意构思，用的是线上或实验室实验；本想法研究科研人员的选题，在学科层面用大规模论文数据观察。
  - rank 9 只在方法上相近：它用动态主题模型追踪 AI 论文自身的主题演变，不问"用 AI 会不会让选题变窄"。
  - 证据表把 rank 2、rank 4 的"研究问题"标为 differ，我不同意：去掉情境之后，问题是同一个——个人用 AI，集体是否趋同。
- 差多大：
  - 只对照这三篇：中等。这是把已知机制搬到新情境，搬迁本身可以撑起一篇论文。
  - 对照真正的最近邻 Hao 等（2026，见第 3 节）：接近零。按 `idea/idea.md` 现在的写法，研究问题、数据与方法、预期发现三个面与它重合；研究情境只差在它限定于自然科学；作用机制它也给出了答案：AI 研究向数据最丰富的领域集中。
  - 这篇不在证据表里：按第 1 节的选择规则，表中没有一篇在"研究问题"面标为 overlap，而它在这一面必然重合。查不到不等于新。
- 还剩的空间（均出自 Hao 等自己写明的边界，供 T7 换面）：
  1. 研究情境：只研究生物、医学、化学、物理、材料、地质六个学科，明确排除了经济学和商科。T7 换这一面。
  2. 数据与方法：只能识别标题、摘要里写明的 AI 使用，作者承认漏掉未写明的使用，例如用大模型辅助构思、检索、写作。
  3. 研究问题：作者承认无法完全确立因果。

## 3. 审稿人最可能说"已被做过"的一条理由及其文献（人填）

- 理由：同一个问题已有人用 4130 万篇论文回答过。使用 AI 的科学家发文是未使用者的 3.02 倍、被引 4.84 倍、早 1.37 年成为项目负责人；但 AI 研究的集体知识广度收缩 4.63%，学者之间的互动减少 22%。不讲清与这篇的区别，本想法会被直接判为重复。
- 文献（作者、年份、题目、DOI 或 arXiv ID；给不出的标 UNVERIFIED）：Hao, Q., Xu, F., Li, Y., & Evans, J. (2026). Artificial intelligence tools expand scientists’ impact but contract science’s focus. Nature, 649(8099), 1237-1243.
