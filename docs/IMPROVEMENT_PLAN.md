# 改进计划：HANDOFF.md 第 9 节的十个遗留问题

> 2026-11-02。先调研、再计划、后实施。本文件说明每个问题的原因、依据、方案、当前状态和验收标准。
> 文中文献的 DOI 都已在 api.crossref.org（arXiv 论文在 OpenAlex）逐条核对，见 `logs/RUN_LOG.md` Step 26。
> GitHub 项目的许可证与星标数据取自 GitHub 搜索 API（2026-11-02），只用作"别人怎么做"的参照，未引入任何外部代码或依赖。
> 本文件不判断新颖性（PROJECT.md 规则 a）。

## 0. 总览

| # | 问题 | 原因 | 方案 | 状态 |
|---|---|---|---|---|
| 1 | v1 漏检 Hao 等（Nature 2026） | 措辞不同：AI 一侧写 "AI tools"，结果一侧写 "narrowing of scientific focus" | 引文追踪：一步前向/后向；两步共被引（引用种子、且属于想法情境的文献共同引用了什么） | 已实现（snowball.py） |
| 2 | v2 混入 "narrow AI" 噪声 | 词干还原后 narrowing = narrow | 检索式支持 `AND NOT (…)`；OpenAlex 原样发送，S2 译为 `+ -(…)` | 已实现，待评估 |
| 3 | 预印本与正式版没有合并 | 预印本标题末尾多了 "(Just accepted by Nature…)" | 比较标题前去掉末尾的发表状态括注；按保守规则自动合并，疑似情况标出待人工核对 | 已实现（merge.py 默认方法） |
| 4 | 前 20 名靠并列决定；S2 偏向高被引老文献 | 按命中次数排序；S2 bulk 只能按被引次数排序 | S2 在取回的全部记录上本地 BM25 重排；合并后按 RRF 排序、BM25 打破并列 | 已实现 |
| 5 | 部分记录没有摘要 | 出版商不开放摘要 | 从同一研究的其他版本补摘要（enrich.py），注明来源 | 已实现 |
| 6 | 落地页核验失败 | 云端网络策略；Emerald、IEEE 的 DOI 登记的是 http:// 地址 | https → http 跳转改用 https；`--no-landing` | 已实现 |
| 7 | arXiv DOI 无法核验 | DataCite 登记，需访问 data.crosscite.org | Crossref 失败时按 DOI 查 OpenAlex | 已实现 |
| 8 | 质量检查没有脚本 | 原为会话中的内联脚本 | `scripts/qa.py`（Porter 词干还原，近似 API 的 KStem） | 已实现 |
| 9 | 年份取最早版本 | 合并时取组内最早年份 | `year` 取正式发表版本的年份，另列 `year_first` | 已实现 |
| 10 | "研究问题"面的标注标准未落实 | — | 按研究者的标准修订两张证据表 | 已完成（Step 25） |

## 1. 召回：v1 漏检 Hao 等

**原因**（Step 11）：参考文献的摘要用 "Artificial Intelligence (AI)"、"AI tools"、"narrowing of scientific focus"、"shrinks the collective volume of scientific topics"，v1 的检索词都匹配不到。关键词检索的固有局限：同一概念有多种说法。

**依据**

- 引文追踪（citation searching / snowballing）是系统综述中补关键词检索漏检的标准做法：Wohlin 2014（doi:10.1145/2601248.2601268）；Greenhalgh & Peacock 2005 发现复杂证据综述中约一半来源靠追踪找到（doi:10.1136/bmj.38636.593461.68）；Hirt 等 2023 范围综述（doi:10.1002/jrsm.1635）与 2024 TARCiS 报告规范（doi:10.1136/bmj-2023-078384）；Linder 等 2015（doi:10.1016/j.jclinepi.2014.10.008）。
- 共被引与文献耦合：Small 1973（doi:10.1002/asi.4630240406）、Kessler 1963（doi:10.1002/asi.5090140103）；基于引文的检索与排序：Belter 2015（doi:10.1002/asi.23605）、Belter 2017（doi:10.1007/s11192-017-2406-y）、Janssens 等 2020 CoCites（doi:10.1186/s12874-020-0907-5）。
- 工具：citationchaser（Haddaway 等 2022，doi:10.1002/jrsm.1563；用 Lens.org）、findpapers、asreview-datatools 的 snowball、openalexR 的 `oa_snowball()` 都用 OpenAlex 或 S2 做前向/后向追踪。
- 相对召回（relative recall）与已知文献检验：Sampson 等 2006（doi:10.1186/1471-2288-6-33）；Cooper 等 2018（doi:10.1016/j.jclinepi.2018.02.025）。原则：不能用同一批已知文献既调参又检验。

**实测**（调研子任务，2026-11-02，OpenAlex 与 S2 实时请求）

- 从 v1 证据表的种子（Doshi & Hauser；Anderson 等）出发，**一步**都到不了 Hao 等：前向引用、后向引用、OpenAlex `related_works`、S2 推荐接口全部漏检。Hao 等没有引用这两篇。
- **两步**可以：先取引用种子的文献（前向），再看它们共同引用了什么（后向，即共被引）。不加过滤时 Hao 等在 34,922 篇被引文献中排第 156；只保留标题摘要命中想法情境词（v1 的 scientist*）的引用者时排第 1（14 篇引用者中有 6 篇引用了它）。用其他面的词过滤则找不到或排在 196、587 位。
- 这个过滤方式是在知道目标的情况下试出来的，只能算一个正例，不能算验证。

**方案**

1. `scripts/snowball.py`（已实现）：一步追踪。种子取证据表中至少 2 个面为 overlap 的文献（研究者可改），按"与几篇种子有引用关系"和"与种子的 TF-IDF 相似度"排序。
2. 共被引模式（`--cocite`，已实现）：前向一步，引用者按研究者指定的词组过滤（默认建议想法"研究情境"面中"谁在用"的词，理由是种子与想法恰在情境面不同）；再后向一步，统计被至少 2 篇引用者共同引用的文献，按支持数、再按支持数 / √被引次数排序。只走两步，不再继续。
3. 结果单独成表（`results/merged/chase_*.csv`），标出已在检索结果中的条目，不并入检索排序；研究者看过后把需要的文献加入证据表。

**验收**：只用 v1 的检索式和 v1 证据表的种子（不使用 Hao 等的任何信息），报告 Hao 等在一步追踪、共被引（情境词过滤 / 其他面过滤 / 不过滤）各列表中的名次，并如实说明过滤方式的来历。

## 2. 噪声："narrow AI"

**原因**（Step 15）：v2 把 "narrowing of science" 放宽为 narrowing，两个 API 都做词干还原，narrow AI、narrow applications 等都被命中，v2 前 10 篇里有 4 篇。

**实测**（调研子任务）

- OpenAlex：大写 `NOT` 有效，`narrowing NOT "narrow AI"` 恰好少掉 "narrow AI" 的命中数；**小写 `not` 和 `-` 不是排除**，OpenAlex 会把要排除的词当作必须包含，检索意思被悄悄反转。
- S2：`-("narrow AI" | "narrow artificial intelligence")` 有效。
- v2 Q3 加 NOT 后：OpenAlex 299 → 247，S2 123 → 111；前 10 的 4 篇噪声只剩 1 篇（"narrow applications"）；参考文献仍在第 1、2 名。去掉的 52 篇 OpenAlex 记录中没有一篇与选题收窄有关。
- 剩下的用法（narrow applications / systems / tasks）列不完，不宜都写进 NOT；改用 `.exact`（不做词干还原）会丢掉其他词形（如 "narrower role sets"）。

**方案**（已实现）：检索式写成 `… AND NOT ("narrow AI" OR "narrow artificial intelligence")`；OpenAlex 原样发送，并检查 `x_query.oql` 中确实出现 NOT，否则报错不保存；S2 译为 `+ -(…)`；`--dry-run` 拒绝小写运算符和以 `-`、`!` 开头的词。本地匹配时，排除组的短语所覆盖的位置不计入匹配。

**研究者决策点**：是否在正式检索式中加入 NOT，以及剩余噪声（narrow applications）的处理：保留 / 加入 NOT / 改用更具体的短语。评估轮（v2b）只作演示，不改动 `queries/queries_v2.json`。

**验收**：v2b 前 10 中 "narrow AI" 类噪声的篇数；参考文献是否仍被检索到。

## 3. 预印本与正式版合并

**原因**：Hao 等的 Nature 版与 arXiv 版在 OpenAlex、S2 中是两条记录，Crossref 也没有关联（`relation` 为空）；预印本标题末尾多了 "(Just accepted by Nature, to be online soon)"，规范化标题不同。

**依据**

- 去重研究：ASySD（Hair 等 2023，doi:10.1186/s12915-023-01686-z）；Rathbone 等 2015（doi:10.1186/2046-4053-4-6）；Jiang 等 2014 刻意偏向"不合并"（doi:10.1093/database/bat086）；McKeown & Mir 2021（doi:10.1186/s13643-021-01583-y）；Guimarães 等 2022（doi:10.1016/j.jclinepi.2022.10.009）；BibDedupe（Wagner 2024，doi:10.21105/joss.06318，以零误并为目标）。
- 预印本—正式版匹配：Cabanac 等 2021（doi:10.1007/s11192-021-03900-7）；PreprintMatch（Eckmann & Bandrowski 2023，doi:10.1371/journal.pone.0281659）；Pre2Pub（doi:10.2196/34072）；PreprintResolver（doi:10.1007/978-3-031-43849-3_5，建议人工核对）；Lin 等 2020 指出标题常有改动（doi:10.1007/s11192-020-03430-8）。
- 工具做法：bib-dedupe 去掉末尾括注并设"非重复"规则；Zotero 要求年份差 ≤1、DOI 不同即不合并；JabRef 按词逐位比较。注意：Zotero、ASySD、bib-dedupe 都会把这一对**分开**（DOI 不同、年份差 2）——系统综述的去重与"同一研究的不同版本"是两个任务。

**方案**（规则在 `scripts/textmatch.py`，由 `merge.py` 默认方法使用）

- 比较用的标题：去 HTML、去重音；末尾最多去掉两个只含发表状态说明的括注（accepted by / to appear / in press / preprint / online soon / under review 等），含更正、撤稿或"第 N 部分"等字样的括注不去；任何非字母数字字符都作分隔；去掉空格后相同也算相同。
- **自动合并**：规范化标题相同（≥5 词），且来信/变体字样不只出现在一侧；不是两个不同的正式发表 DOI；都不是数据集 DOI（Zenodo、figshare、IEEE DataPort 等）；年份相差 ≤3；两边都有摘要时摘要词集合 Jaccard ≥0.5。
- **只标出、不合并**：标题相同但不满足上述条件；标题几乎相同（difflib ≥0.90 且词 Jaccard ≥0.80，或较短标题完整包含在较长标题中）。
- "Re: <标题>"这类关于另一篇的条目不合并。
- DOI 比较前去掉 `?utm_source=…`、`/full/html` 之类的落地页后缀（v1 中有一例）。

**实测**（接入 merge.py 后在已提交的 v1、v2 原始数据上运行，与调研子任务的只读原型一致）：新增合并只有 Hao 这一对；旧方法按标题合并的组（v1、v2 各 7 组）各保留 6 组，拆开的只有 IEEE DataPort 数据集与同名 TechRxiv 预印本（改为待核对）；ICAITE 会议论文与同名 Zenodo 存档（标题只差 "Problemsolving" / "Problem-Solving"）新标为待核对。

**验收**：v2b 中 Nature 版与 arXiv 版并为一篇；人工核对全部新增合并组与待核对组。

## 4. 排序

**原因**：合并后按命中次数（出现在几个"检索式 × 来源"列表中）排序，两轮的前 20 都出自并列组；S2 bulk 不按相关度排序，原先取被引次数最高的 25 条（v2 Q3 的 S2 前 25 中有 1984、1997 年的文献）。

**依据**

- BM25：Robertson & Walker 1994（doi:10.1007/978-1-4471-2099-5_24）、Robertson & Zaragoza 2009（doi:10.1561/1500000019）；变体比较：Kamphuis 等 2020（doi:10.1007/978-3-030-45442-5_4）。
- 布尔结果集内再排序：Salton, Fox & Wu 1983（doi:10.1145/182.358466）；Karimi 等 2010（doi:10.1186/1472-6947-10-58）。协调级匹配：Losee 1987（doi:10.1002/(sici)1097-4571(198707)38:4<239::aid-asi4>3.0.co;2-6）。
- 倒数排名融合 RRF：Cormack, Clarke & Buettcher 2009（doi:10.1145/1571941.1572114），score = Σ 1/(60 + 名次)。
- 筛选优先排序（ASReview，van de Schoot 等 2021，doi:10.1038/s42256-020-00287-7）需要人工标注和机器学习库，不适合本项目的纯标准库流程，只借鉴"按与查询文本的相似度排序"的思路。

**实测**（调研子任务，用已提交的 v2 数据离线比较）：RRF 的前 20 有 19 个不同分值（原来 32 篇并列在截断处），与原前 20 有 18 篇相同；噪声论文仍在前列——**重排不能解决匹配问题**，噪声要靠第 2 节解决。两个来源都改用本地 BM25 时，参考文献从第 3 名掉到第 23 名（两个 API 都不给它的摘要），所以 OpenAlex 保留 API 的相关度排序。

**方案**

- S2（已实现）：翻页取回全部命中（最多 3000 条），本地重排：满足的包含组数 → BM25（k1=1.2，b=0.75，Lucene IDF）→ 被引次数。没有摘要的记录单独排序：标题至少命中（组数 − 1）个组的，按无摘要记录的比例分配名额并穿插。
- 合并后：按 RRF（k=60）排序，BM25（全部检索词，排除组短语不计）打破并列，再按 merged_id；命中次数、本地满足的检索式条数只作显示列。
- 保留旧方法：`merge.py --legacy` 逐字节复现已提交的 v1、v2 结果。

**验收**：截断处的并列篇数；前 20 中满足检索式（本地近似）的比例、带生成式 AI 关键词的比例、年份分布。

## 5–9. 其余问题

| # | 方案 | 验收 |
|---|---|---|
| 5 无摘要 | `enrich.py`：按题目在 OpenAlex 查同一研究的其他版本，要求标题相同（≥6 词）、年份差 ≤3、至少一位作者同姓；补到的摘要连同来源写入 `evidence/enrichment*.json`，不改动 results/ | v2 前 20 缺摘要 2 篇，补回 1 篇（M003 ← arXiv 2412.07727） |
| 6 落地页 | https → http 跳转改用 https；`--no-landing` 只做元数据核验 | Emerald、IEEE 由"域名解析失败"变为与其他出版商一致的结果 |
| 7 arXiv DOI | Crossref 失败时按 DOI 查 OpenAlex | v2 rank 9（doi:10.48550/arxiv.2506.21818）核验通过 |
| 8 质量检查 | `qa.py`；注明是用 Porter 词干还原近似两个 API 的 KStem（调研实测两者都像 Krovetz 词干还原，Porter 更宽松，所以比例偏高） | 复现 Step 4、13、15 的数字 |
| 9 年份 | `year` 取正式发表版本：带正式发表 DOI 的记录中，先取不带 arXiv ID 的记录的最早年份（带 arXiv ID 的是预印本与正式版合成的记录，S2 常记成预印本年份），没有时取 OpenAlex 的年份；`year_first` 记最早版本。已提交数据中两个来源年份不一致的 4 个 DOI 都按此取对（含 OpenAlex 把 1993 年 HICSS 论文记为 2002 的一例） | Hao 等合并后 `year`=2026、`year_first`=2024 |

## 10. 评估设计

两轮评估，输出用新后缀，不覆盖 v1、v2 的结果：

- **v1b**：v1 的检索式不变，用改进后的流程（S2 重排、合并新规则与 RRF、补摘要、引文追踪，种子取 v1 证据表）。用于检验召回（Hao 等）与排序。
- **v2b**：v2 的检索式加 NOT（只加在含 narrowing 的 Q2、Q3、Q6），其余同上。用于检验降噪、合并、年份。

指标：参考文献在候选与追踪列表中的名次；前 10 / 前 20 的噪声篇数；截断处并列篇数；前 20 满足检索式的比例、带生成式 AI 关键词的比例、年份中位数；新增合并与待核对组；前 20 有摘要的比例（补摘要前后）；核验成功率。

局限：v2 的检索词与 v2b 的 NOT 短语都是在看过结果之后定的，v2b 只说明修正对已知问题有效；v1b 的共被引过滤方式也是在知道目标后试出的。这些都不是独立验证。

## 11. 研究者决策点

1. 是否在正式检索式中采用 NOT，以及剩余噪声的处理（第 2 节）。
2. 引文追踪的种子（默认取证据表中 ≥2 个面为 overlap 的文献）和共被引的过滤词组（第 1 节）。
3. v2 证据表 rank 8 的"研究问题"面按研究者标准改为 overlap，是助手的推断，请确认（Step 25）。
4. 是否用 v1b、v2b 的结果替代原来的 v1、v2 结果。
