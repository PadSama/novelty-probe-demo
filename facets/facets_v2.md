# 想法拆解 v2（facets）

> 来源：`idea/idea_v2.md`。本文件只拆解想法、设计检索词：不判断新颖性，不列文献。

**想法原文（v2）**：我注意到身边越来越多人用 AI 做研究。我想研究：管理学与经济学领域的研究者使用 AI 工具，会不会让这两个学科的选题变窄？打算用大规模论文数据来测。

**相对 v1 的改动**：v1 原文为"科研人员使用 AI 工具，会不会让整个学科的选题变窄"，没有限定学科（v1 的检索词如 AI for science、scientists 偏向自然科学）。v2 把研究情境限定为管理学与经济学研究。

**沿用的研究者决定**："AI 工具"只指生成式 AI（2022 年底以后）。检索词保留更宽的 AI 说法，范围在筛选时用产品与公司关键词判断（LLM、ChatGPT、Gemini、Claude、OpenAI、Anthropic 等）。concurrent 检索式只取 2023 年起的文献。

## 总览

| # | 面 | key（queries_v2.json 用） | 想法中对应的内容 |
|---|---|---|---|
| F1 | 研究问题 | `research_question` | 研究者使用 AI 工具 → 选题范围是否收窄；AI 工具的各种说法集中放在本面 |
| F2 | 作用机制 | `mechanism` | AI 使用通过什么途径影响选题（原文未说明，下面列的是候选机制） |
| F3 | 研究情境 | `context` | 谁在用：管理学与经济学研究者；另列 scientists 作跨情境对照 |
| F4 | 数据与方法 | `data_method` | 大规模论文数据：怎么测 AI 使用、怎么测选题范围、怎么做因果识别 |
| F5 | 预期发现 | `expected_findings` | 选题变窄（含中性测度与一个反向结果词） |

类型标注：**核心** = 想法本身的说法；**同义** = 同一概念的其他说法；**相邻学科 / 相邻情境** = 其他学科或情境的叫法；**反向** = 与预期相反的结果。⚠ = 检索时容易混入的同名概念。

---

## F1 研究问题 `research_question`

自变量是研究者使用 AI 工具，因变量是选题范围。AI 工具的四种说法都放在本面，个人层的因变量也放在本面；学科层的测度放在 F5。

| # | 检索词 | 类型 | 说明 |
|---|---|---|---|
| 1 | "AI tools" | 核心·自变量 | 想法原文"AI 工具"的直译 |
| 2 | "artificial intelligence" | 核心·自变量 | 全称；也能匹配 "generative artificial intelligence" |
| 3 | "generative AI" | 核心·自变量 | 研究者限定的范围 |
| 4 | "large language models" | 核心·自变量 | 生成式 AI 的主要工具 |
| 5 | "research topic selection" | 核心·因变量（个人层） | 对应"选题" |

## F2 作用机制 `mechanism`

想法原文没有说明机制。与 v1 相同的五个候选机制，只用于检索；是否成立要看文献证据。

| # | 检索词 | 类型 | 说明 |
|---|---|---|---|
| 1 | homogenization | 核心 | 大家用同一类模型，产出趋同；检索式中写作 homogeniz* / homogenis*。⚠ 材料、力学中有同名概念 |
| 2 | "algorithmic monoculture" | 同义（系统层）·相邻学科（计算机科学） | 大量使用者依赖同一模型，判断彼此相关 |
| 3 | "streetlight effect" | 相邻学科（科学哲学/经济学） | 研究向数据和工具好用的问题集中 |
| 4 | "exploration-exploitation" | 相邻学科（组织学习/管理学） | 工具提高"利用"已知方向的回报，挤出"探索"。⚠ 强化学习中有同名概念；管理学中大量文献讨论企业层面的探索与利用 |
| 5 | "Matthew effect" | 相邻学科（科学社会学） | AI 检索和推荐放大高被引文献，注意力更集中 |

## F3 研究情境 `context`

| # | 检索词 | 类型 | 说明 |
|---|---|---|---|
| 1 | economists | 核心·使用者 | 检索式中写作 economist* |
| 2 | "economic research" | 核心·学科 | ⚠ "AI 对经济的影响"类文献很多，需与研究活动的词组合 |
| 3 | "management research" | 核心·学科 | ⚠ "implications for management research" 这类套话常见 |
| 4 | "business research" | 同义·商科 | |
| 5 | scientists | 相邻情境 | 跨情境对照（自然科学等其他学科），只用于 Q3；检索式中写作 scientist* |

## F4 数据与方法 `data_method`

与 v1 相同。分三个子问题：怎么识别论文用了 AI（测自变量）、怎么测选题范围（测因变量）、怎么做因果识别。

| # | 检索词 | 类型 | 说明 |
|---|---|---|---|
| 1 | "science of science" | 核心（领域名） | |
| 2 | bibliometrics | 同义（情报学/科学计量学） | 检索式中写作 bibliometric*。⚠ 与 AI 词组合时会带出大量"某领域的文献计量综述" |
| 3 | "topic modeling" | 核心·测因变量 | |
| 4 | "LLM-generated text" | 核心·测自变量 | 在大规模论文中识别 LLM 使用 |
| 5 | "difference-in-differences" | 相邻学科（计量经济学）·因果识别 | |

## F5 预期发现 `expected_findings`

想法预期的方向是"选题变窄"。第 2 个词是中性测度，第 5 个是反向结果，用来同时找到不支持这一预期的证据。

| # | 检索词 | 类型 | 说明 |
|---|---|---|---|
| 1 | narrowing | 核心 | v1 用的是短语 "narrowing of science"，v2 放宽为单词（词干还原后也匹配 narrow、narrower）。⚠ "narrowing the gap" 这类说法常见 |
| 2 | "topic diversity" | 核心·学科层（中性测度） | ⚠ NLP 中也指主题模型的评价指标 |
| 3 | "topic concentration" | 同义（科学计量学） | |
| 4 | "collective diversity" | 相邻学科（创造力研究） | 群体层面的产出多样性，区别于个人层面 |
| 5 | "research diversification" | 反向 | 选题变宽 |

---

## 与 v1 的差异及原因

| 改动 | 原因 |
|---|---|
| F3 改为 economists、"economic research"、"management research"、"business research"，另加 scientists 作跨情境对照 | 研究者把情境改为管理学与经济学研究 |
| 去掉 "AI in science"、"AI for science"、"direction of science" | 自然科学取向的说法，不适合 v2 情境 |
| 加入 "AI tools"、"artificial intelligence"（F1） | v1 漏检研究者给出的参考文献（Hao 等，Nature 2026）。诊断见 `logs/RUN_LOG.md` Step 11：其预印本摘要用的是 "Artificial Intelligence (AI)"、"AI tools"，不满足 v1 任何一条检索式 |
| "narrowing of science" 放宽为 narrowing（F5） | 同上：该摘要写的是 "narrowing of scientific focus"，v1 的短语匹配不到 |
| 去掉 "machine learning" | 研究者已限定为生成式 AI；更宽的说法由 "artificial intelligence" 覆盖。v1 中它带来 1993 年的机器学习论文（v1 证据表 rank 8） |
| 去掉 "problem choice" | v1 中因标点被去掉而误命中（v1 证据表 rank 8 的 "the problem, choice of a representation"） |
| 去掉 "disruptiveness" | 管理学中与 "disruptive innovation" 词干相同，噪声大 |
| AI 工具的各种说法从 F3 移到 F1；"topic diversity" 从 F1 移到 F5 | F3 改为只描述"谁在用"；每面最多 5 个词 |

注意：v2 的检索词是在知道 v1 漏检原因之后调整的，因此 v2 若检索到 Hao 等，只能说明这次修正生效，不能当作独立的召回验证。

---

## 附：检索式约定（`queries/queries_v2.json`）

- 检索式只用上面表里的词，只加词尾截断（*）和英式拼写变体（homogenis*）。
- 写法是通用布尔式：引号 = 短语，* = 词尾截断，AND / OR / 括号。执行时由 `scripts/search.py` 转换成各数据源的语法。
- `purpose` 取值：
  - **component**：想法的某个组成部分（某个机制，或目标学科中的某个结果），不要求其他组成部分同时出现。
  - **application**：同一关系或机制放在科研情境里（v2 分为跨情境与目标情境两条）。
  - **method**：可借用的数据与方法（测 AI 使用、测选题、因果识别）。
  - **concurrent**：近期同题工作，含预印本；执行时只取 2023 年起的文献。

| id | purpose | 查什么 |
|---|---|---|
| Q1 | component | 生成式 AI 是否让产出趋同（机制），不限情境（与 v1 Q1 相同） |
| Q2 | component | 管理学与经济学研究的选题收窄、集中或多样化，不限原因 |
| Q3 | application | 跨情境：AI 使用与科学家选题范围的关系（自然科学等其他学科） |
| Q4 | application | 目标情境：路灯效应、马太效应、探索–利用等机制与管理学和经济学研究中的 AI 使用 |
| Q5 | method | 识别论文中的 LLM 使用、测选题、因果识别的方法（与 v1 Q5 相同） |
| Q6 | concurrent | 近期直接检验"AI 与管理学/经济学研究选题范围"的工作 |
