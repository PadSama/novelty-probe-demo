# 工具层架构审视与迭代计划

> 2026-11-02。研究者的要求：教程部分到此为止，不再追求某一轮结果更好；迭代对象是承重层工具本身——**准确性、稳定性、适配性**，为后续实用化做准备。
> 本文件是审视（现状 → 问题）、调研（成熟项目怎么做）、方案（目标架构）与分阶段计划。调研由三个并行子任务完成（成熟项目架构；HTTP 层与测试；适配性），所引项目的源码均实际下载阅读，所引接口行为均于当日实测；主会话复核了其中的关键结论。文件路径与版本见第 8 节。
> 本文件不涉及新颖性判断（PROJECT.md 规则 a）。

## 0. 结论先行

| 维度 | 现状 | 目标 |
|---|---|---|
| 准确性 | API 的实际语义只记录在日志里；OpenAlex 对**未配对引号**不报错而把运算符当成词（count 从几百变成两万多），当前只检查了 NOT 一种情况；质量检查用 Porter 近似 KStem，没有量化 | 客户端边界做契约校验（OpenAlex 返回的 `x_query.oqo` 与本地解析树结构比对；S2/Crossref 的响应形状校验）；录制的真实响应作为测试件；每次运行记录 API 的解析结果 |
| 稳定性 | 两套 HTTP 代码；无缓存、无回放、无断点续跑；S2 一半请求被拒只能靠退避；非 JSON 的错误体（OpenAlex 404 是 HTML）泄漏到报错里；写文件不是原子的；没有运行清单 | 一个 HTTP 客户端：按主机限速、读 Retry-After 与额度头、全抖动退避、熔断、内容寻址缓存、`live / cache / record / replay` 四种模式、断点续跑、原子写、运行清单 |
| 适配性 | 五个面、中文列名、截断词表、停用词、DOI 前缀表、关键词表、所有阈值都写死在代码里；英文表头的证据表让引文追踪拿到零种子（已复现）；带 BOM 的 JSON 读不进去（已复现）；测试与教程数据绑定，按 HOWTO 清空示例后测试必失败；没有包结构 | 一个配置文件（JSON）承载所有可变项；中英文可切换的消息表；证据表以 JSON 为事实来源、Markdown 由渲染生成；查询先解析为 AST 再按数据源序列化；数据源适配器协议；`novelty_probe/` 包 + `scripts/` 薄壳，命令行用法不变 |

## 1. 现状盘点（2026-11-02，主会话实测）

- 10 个脚本 2736 行 + 2 个测试文件 1037 行；最大 merge.py 584、search.py 510。
- 顶层常量约 95 个，散在 9 个文件；其中 19 个路径常量全部绑定 `ROOT = Path(__file__).resolve().parent.parent`，`rel()` 重复 5 次。
- 跨脚本 import 12 处：search ← {authors, enrich, merge, qa, snowball, compare}；textmatch ← 6 个脚本；merge ← {qa, compare}。没有包，靠 `sys.path[0] == scripts/` 成立；模块名 `search`、`merge` 极易与第三方包同名。
- HTTP：`search.get_json`（JSON、重试、S2 节流）与 `verify.fetch`（跟随跳转、记录跳转链）两套；11 个调用点；没有缓存；重试间隔 2/4/8 秒，不带抖动。
- 记录模型：8 个字段的字典，其他脚本按键直取（`doi` 17 处、`title` 12 处）；无 schema、无版本号；原始 API 响应体丢弃（所以要靠 authors.py、enrich.py 再去查作者和摘要）。
- 用户可见字符串：中文写在代码里（search.py 29 行、snowball.py 13 行）；verify.py 把"题目一致"这样的中文写进了数据文件。
- 全局可变状态：`textmatch._cache`、`search._last_s2_request`；测试靠 `mock.patch.object` 改模块变量，说明"配置"就是模块变量。
- 兼容性：46 个测试在 Python 3.9、3.10、3.11、3.12、3.13（Linux）全部通过；`Path.is_relative_to` 需 3.9；Windows 未测，静态检查发现直接运行脚本时向 cp936/cp1252 控制台打印 "→"、"·" 可能抛编码错误；文本写入没有指定 `newline`，Windows 上会写出 CRLF；HOWTO 的 21 条命令写 `python3`，共被引那条用单引号传参（cmd.exe 下会原样传入）。
- 测试：全部离线，用本机模拟服务器；但 API 响应形状是手写的，API 变更不会被发现；多项测试依赖仓库里的教程数据（`queries.json` 必须是 Q1–Q6、证据表必须 10 行中文列名）。

## 2. 问题清单

编号前缀：A 准确性、S 稳定性、P 适配性。"实测"指主会话或调研子任务当日对真实 API 的观察。

| # | 问题 | 证据 | 影响 |
|---|---|---|---|
| A1 | OpenAlex 对格式错误的检索式静默改写 | 实测：`("generative AI OR ChatGPT) AND science` → 200，oql 为 `(generative AI "OR" ChatGPT "AND" science)`，count 21,344；小写 `not` 变成普通词 | 检索结果与意图不同而无人察觉；现只检查 NOT |
| A2 | 非 JSON 错误体 | 实测：OpenAlex `/works/doi:<不存在>` → 404 HTML；Crossref 404 → 纯文本 `Resource not found.` | `api_error()` 把 HTML 片段写进报错 |
| A3 | 响应形状无校验 | S2 的 429 体是 `{"message","code"}`，其他 4xx 是 `{"error"}`；`abstract` 文档明说可能缺失 | 字段改名、类型变化时静默出错 |
| A4 | 质量检查是近似 | Porter 比 API 的 KStem 宽松（实测 news≠new、universe≠university） | 比例偏高，未量化 |
| A5 | 评估与教程想法耦合 | compare.py 的 GENAI_TERMS 是本想法专用 | 换想法后 "genai" 列无意义 |
| S1 | 无缓存、无回放 | OpenAlex 本 key 每日 10,000 credits（≈1,000 次列表请求，实测头 `X-Ratelimit-Limit: 10000`），共用；S2 即使间隔 2 秒仍约半数 429（实测，无 Retry-After） | 每次重跑都花额度、都挨 429；测试无法用真实响应 |
| S2 | 两套 HTTP 代码 | search.get_json 与 verify.fetch | 退避、超时、错误分类不一致 |
| S3 | 退避无抖动、不读额度头、无熔断 | OpenAlex 每个响应都带 `X-Ratelimit-Remaining`；S2 持续 429 时每条检索式都慢慢重试 | 预算耗尽前没有预警；长流程卡住 |
| S4 | 无原子写、无断点续跑 | `write_text` 直接覆盖；S2 翻页 3000 条、引文追踪 1000+ 篇中途失败需从头跑 | 半个文件；重复花额度 |
| S5 | 无运行清单 | 输入、参数、版本、产出哈希只在 RUN_LOG 的人写文本里 | 无法机器核对"同一检索式、不同日期"的漂移 |
| S6 | DataCite DOI 走必败的一跳 | Crossref 有 `/works/{doi}/agency`（实测返回 `datacite`） | 可以先判断登记机构再决定去哪里核验 |
| P1 | 面的名称写死 | snowball.FACETS 中文；英文表头 → 零种子（已复现） | 英文用户无法用引文追踪 |
| P2 | 配置项散在代码里 | TRUNCATION（5 个词）、STOPWORDS、PREPRINT/DATA DOI 前缀、notice 词、GENAI_TERMS、TOP_N/TOP_K/RRF_K/YEAR_WINDOW/k1/b…；HOWTO 甚至写"修改 scripts/search.py 中的 CONCURRENT_FROM_YEAR" | 换想法要改源码 |
| P3 | 文件名即契约 | `Q\d+`、`{source}_Q\d+{suffix}` 在三处用正则各自实现；compare.py 为此写了 `_` 的特判 | 加数据源、改编号要改多处 |
| P4 | 中文硬编码、数据里混入展示文字 | verify 的"题目一致 / 落地页"写进表格；CLI 帮助与报错只有中文 | 不能切换语言；数据不可机器读 |
| P5 | Markdown 是事实来源 | verify.py 原地改写 Markdown；snowball、tests 各自再解析一遍 | 结构化信息（结构化核验结果、引文出处、修订历史）放不进去 |
| P6 | 数据源与查询翻译耦合 | SEARCHERS 字典 + 两个翻译函数各自重新分词 | 加 Crossref/PubMed/arXiv 要改 search.py 主流程 |
| P7 | 无包结构 | 见第 1 节 | 不能 `pip install -e .`，不能在别的目录运行 |
| P8 | 读写编码与换行 | BOM 读失败（已复现）；写入无 `newline="\n"`；无 `.gitattributes` | Windows 用户第一步就卡住 |
| P9 | 测试与教程数据绑定 | 见第 1 节 | HOWTO §1 清空示例后 AGENTS.md 的"测试全过"无法满足 |
| P10 | 文档命令只适用 POSIX shell | `rm -f … && printf …`、单引号参数、`python3` | Windows 用户需要翻译命令 |

## 3. 成熟项目怎么做（调研摘要）

读过源码的项目：CoLRev 0.16.2（含 search-query、bib-dedupe）、findpapers 0.6.7、litstudy 1.0.6、pyalex 0.21、paperfetcher 1.2.2、ASReview 3.0.8 数据层、openalexR、pybliometrics 4.5、SnowBallSLR；工具库 vcrpy、requests-cache、urllib3 Retry、tenacity；OpenAlex 文档镜像、S2 swagger。

| 主题 | 做法 | 借鉴 |
|---|---|---|
| 布局与配置 | CoLRev：单包、插件实现 ABC、项目级 settings.json、密钥不进配置；SnowBallSLR：配置里只写环境变量名，`config_hash` 剔除密钥，命名退出码；openalexR：未知配置键报警告 | 包 + 薄壳；配置只放环境变量名；config_hash 写进每个输出的 meta；退出码统一 |
| 记录与出处 | CoLRev：`colrev_origin`（原始文件/编号，合并时取并集，可撤销合并）、逐字段出处、状态枚举、原始文件保留原字段名；SnowBallSLR：`Provenance(provider, direction, parent, iteration, retrieved_at, response_hash)`、`field_conflicts()` 不吞冲突；litstudy：共有标识符全部相等才算同一篇 | `hits[]` 替代 `raw_refs`、`field_source{}` 记每个字段来自哪条记录、`schema` 版本号、原始响应体进缓存 |
| HTTP | SnowBallSLR：内容寻址缓存 `cache/<2hex>/<sha256>.json`、离线模式；CoLRev：Crossref 读 `x-rate-limit-*` 自适应；openalexR：Retry-After 否则 2^n、上限 30 秒；OpenAlex 文档：只重试 429/≥500、403 是"慢一点"、超时 30 秒；vcrpy/requests-cache：规范化 URL 作键、按录制顺序回放、敏感信息脱敏 | 一个 Client；缓存 + 录制回放；按主机限速；全抖动退避；熔断；额度头进 meta |
| 查询与数据源 | search-query：AST + 每平台 parser/serializer/translator/linter（带位置的错误码）；CoLRev：分页前告知用户总数与预计耗时；findpapers：不支持的特性→跳过该库而不是改写 | 保留受限语法（AND 的 OR 组 + 尾部 NOT；GLM 等助手已能稳定产出），内部 AST + 每源序列化器；分页前估算 |
| 去重 | bib-dedupe：规则字符串可读、`maybe_cases.csv` 人工决定后回读；CoLRev：同源合并高风险、跨层级合并禁止、可撤销；SnowBallSLR：两个不同 DOI 阻断、`max_cluster_size`、`MergeEvent` 可审计、幂等与顺序无关的性质测试 | 决策 JSONL + 人工复核 CSV 回读；簇大小上限；性质测试 |
| 导出与报告 | CoLRev/SnowBallSLR：RIS/BibTeX/CSV 手写约 60 行；PRISMA 计数；RunManifest（版本、config_hash、输入输出哈希）；SnowBallSLR 的 `verify` 从缓存回放并给出漂移分类 | export.py、manifest、PRISMA-S 风格计数（Rethlefsen 等 2021，doi:10.1186/s13643-020-01542-z，已核对） |
| 事实来源 | CoLRev records.bib；ASReview 列名别名 + 标签列；Rayyan 把决定放进 notes 字段——都把记录身份与标签/出处分开，人看的视图是派生的 | evidence JSON + 渲染 Markdown |
| 反模式 | findpapers 轮换 UA、吞掉所有异常；litstudy 固定 sleep 当限速；paperfetcher 单元测试打真网；pybliometrics 轮换 key 躲 429；pyalex 默认不重试 | 测试禁网；不轮换 key；错误分类明确 |

## 4. 目标架构

```
novelty_probe/                 核心层（纯标准库，Python 3.9+）
  __init__.py      __version__, SCHEMA_VERSION
  config.py        load_config(root, overrides) → Config；默认值 + novelty-probe.json 深合并；未知键警告；config_hash
  paths.py         find_root(--root > $NOVELTY_PROBE_ROOT > 向上找 novelty-probe.json > 脚本上级)；rel() 输出 POSIX 分隔符
  io.py            load_json_lenient（utf-8-sig、去 ``` 围栏）、atomic_write、write_csv（BOM）、stdout UTF-8 守卫
  i18n.py          MESSAGES 表 + t(key, **kw)；语言：--lang > $NP_LANG > 配置 > zh
  http.py          Client（live/cache/record/replay；按主机令牌桶；Retry-After/额度头；全抖动退避；熔断；错误分类；paginate；follow）
  cache.py         内容寻址缓存 .cache/http/<host>/<2hex>/<sha256>.json；录制件 tests/fixtures/cassettes/*.json 同一条目格式
  schemas.py       expect() 校验器：OpenAlex/S2/Crossref 响应形状；本项目各文件的 schema
  query.py         parse → Query(include, exclude, raw)；QueryError(code, message, position)；每源序列化器注册表；evaluate()
  text.py          现 textmatch.py（不变）
  record.py        Hit、Record 数据类；规范化函数；schema 升级
  sources/         base.py Source 协议（name, capabilities, translate, search, lookup, references, cites, to_record）
                   openalex.py  semanticscholar.py  crossref.py（有损：词袋 + 本地过滤）
  dedupe.py        现 merge.py 的分组与版本识别 → Decision(a, b, verdict, rule, reason, score)；decisions.jsonl；review CSV 回读
  rank.py          RRF、BM25 排序
  evidence.py      evidence JSON 的读写与校验（标签取值、引文逐字、标识符来自检索结果）；import-md；render → Markdown
  export.py        RIS / BibTeX / CSL-JSON / CSV
  report.py        RunManifest、PRISMA 风格计数
  cli.py           子命令：search qa merge authors enrich verify chase compare export render check
scripts/*.py                   薄壳：from novelty_probe.cli import main; sys.exit(main(["search", *argv]))
novelty-probe.json             项目配置（无密钥）
examples/v1, v2, v1b, v2b      教程产出（测试件从这里读）
tests/                         test_*.py：纯函数、假传输层、录制件回放、契约校验、性质测试、可选的实时金丝雀
```

设计决定与理由：

1. **配置用 JSON**，不用 TOML（`tomllib` 要 3.11）或 INI（无嵌套）。全流程已是 JSON，助手写 JSON 可靠；以 `_` 开头的键作注释；`*_extend` 列表追加到默认值。
2. **保留受限的检索式语法**。S2 本地重排的"命中组数"、`n_conform`、qa.py 都依赖 AND-of-OR 的形状；GLM 的失败全是格式错误，`--dry-run` 已能拦住；换成任意嵌套只会扩大出错面。内部解析一次成 AST，序列化器不再各自分词。
3. **evidence JSON 是事实来源**，Markdown 渲染生成。verify 写结构化结果码（service、http、title_match），不写中文句子；渲染时按语言生成。助手仍可按现有提示词写 Markdown，由 `evidence import-md` 转成 JSON（过渡期保留）。
4. **缓存与录制件同一格式**：键 = sha256(method, 规范化 URL（去 api_key/mailto、排序参数）, Accept, body 哈希)；头部白名单；密钥脱敏；429/5xx 不缓存；404 负缓存 1 天；分页集合条目记录 next 游标用于续跑。正式 T3–T5 运行默认 `live`（results/raw 仍是检索记录），meta.http 记录模式与命中数，读者可分辨网络与缓存。
5. **退避带全抖动**（S2 的 429 是争用型的，实测与间隔无关）；SnowBallSLR 为确定性不用抖动，本项目的确定性由缓存和录制件保证，不靠退避序列。
6. **方法常量不进配置**：Porter、BM25/RRF 公式、版本识别规则顺序、DOI/arXiv 正则、AND NOT 的大写要求。它们是"方法"，变了就不可比；可调的是参数（k1、b、RRF_K、YEAR_WINDOW、MIN_TITLE_WORDS、TOP_N/TOP_K）。
7. **包 + 薄壳**：AGENTS.md、HOWTO 的命令 `python3 scripts/x.py …` 全部保持可用；测试改为 import 包。模块改名避免与第三方包冲突。
8. **向后兼容**：`merge.py --legacy` 继续逐字节复现 v1、v2；旧格式的 results/raw 文件（无 `local_rank`、无 `schema`）仍可读。

## 5. 分阶段计划

每阶段结束：`python3 -m unittest discover -s tests -v` 全部通过（3.9–3.13）；RUN_LOG 记一步；提交推送。

| 阶段 | 内容 | 验收 |
|---|---|---|
| **0 卫生** | 教程产出复制到 `examples/`，测试件改从那里读，读实时数据的测试加 `skipUnless`；`load_json_lenient`（BOM、围栏）；所有文本写入 `newline="\n"`；`.gitattributes`；stdout UTF-8 守卫；snowball 接受英文表头（临时别名表，阶段 2 由配置接管）；logrun 在 Windows 上用 `list2cmdline` 并记录 argv JSON | 按 HOWTO §1 清空示例后测试仍全过；BOM/围栏 JSON 可读；英文表头给出种子 |
| **1 HTTP 层** | `novelty_probe/http.py`、`cache.py`、`schemas.py`、`io.py`、`paths.py`；search/verify/snowball/enrich/authors 全部经 Client；`--http-mode`、`--offline`、`--refresh`；A1 的 oqo 结构校验与"引号内运算符"检查；A2 按 Content-Type 分支；S6 agency 预检；原子写；断点续跑；假传输层测试；录制一套真实响应作测试件；meta.http | 假传输测试覆盖 Retry-After/预算/抖动边界/熔断/断点；回放模式下跑完一轮 search+merge+verify 不联网；额度头进 meta |
| **2 配置与国际化** | `config.py` + `novelty-probe.json`（facets/labels/columns/queries/sources/http/merge/versions/snowball/compare/verify）；`i18n.py` 消息表，`--lang`/`NP_LANG`；evidence JSON schema + `evidence.py`（check/import-md/render）；verify 写结构化码；compare 的关键词表来自配置 | 同一命令 `--lang en` 输出英文；英文证据表全流程可用；`evidence check` 能抓出非逐字引文和不在检索结果里的 DOI |
| **3 查询与数据源** | `query.py` AST + 每源序列化器 + 错误码；`sources/` 协议与注册表；Crossref 有损适配器（默认关闭）；分页前估算（总数、页数、OpenAlex 成本）；golden 三元组、round-trip、性质测试 | 新增一个数据源只需一个模块 + 一个序列化器 + 测试件；dry-run 对不支持的特性打印 SKIPPED |
| **4 记录、去重、导出、报告** | `record.py`（authors、ids、hits[]、field_source、schema）；`dedupe.py` 决策 JSONL + `dedupe_review.csv` 回读 + 簇大小上限 + 同源警告 + 性质测试；`export.py`；`report.py`（manifest、PRISMA 计数）；`cli replay` | 合并决策可追溯到规则编号；人工复核结果下次运行生效；RIS/BibTeX 导出能被 Zotero 读入（本地验证由研究者做） |
| **5 打包与文档** | `novelty_probe/` 包、`pyproject.toml`（无依赖）、`scripts/` 薄壳；HOWTO/HANDOFF/AGENTS/README 更新（PowerShell 列、`py -3`）；可选 GitHub Actions 矩阵 | `pip install -e .` 后 `novelty-probe search --dry-run` 可用；旧命令不变 |

阶段 0、1 不涉及研究者的决策，直接实施；阶段 2 起的决策点见第 6 节。

## 6. 研究者决策点（附建议与理由）

1. **证据表的编写格式**。建议：事实来源改为 JSON，助手仍可写 Markdown 再由 `evidence import-md` 转换；渲染出的 Markdown 供人阅读。理由：结构化核验结果、引文出处、修订历史放不进 Markdown；JSON 可机器校验"引号内文字逐字来自摘要"这条规则；保留 Markdown 入口不改变现有提示词。
2. **是否加入 Crossref 作为第三个检索源**。建议：实现适配器但默认关闭。理由：Crossref 的 `works?query.bibliographic=` 不支持布尔和短语，只能词袋检索后本地过滤，召回不可控；但它可达、有摘要字段，作为可选补充和作为数据源协议的第一个外部实例有价值。arXiv、PubMed 在云端被拦，本地可用，适配器留接口。
3. **测试是否打真网**。建议：单元测试全部禁网（录制件回放）；另设可选的实时金丝雀测试（`NP_LIVE=1`，≤6 个请求），建议每轮 T3 之前跑一次。理由：API 行为在变（OpenAlex 的通配符文档已过时、polite pool 已退役），只有真实请求能发现漂移，但不能让日常测试依赖网络和额度。
4. **是否启用 GitHub Actions**。建议：启用，矩阵 Python 3.9–3.13 × Ubuntu/Windows/macOS，只跑离线测试。理由：Windows 在云端测不了，这是唯一能持续验证编码、换行、路径问题的途径；全是标准库，矩阵运行只需几分钟。需要你在仓库设置里允许 Actions。
5. **PR 流程**。建议：每个阶段结束由我开 PR 并订阅，你审阅合并。理由：你已同意订阅；PR 说明由我写可节省你的操作。
6. **退避是否带抖动**。建议：带（全抖动）。理由：S2 的 429 与间隔无关、呈争用型；确定性由缓存和录制件保证。

## 7. 不做的事

- 不再为提高 v1、v2 的结果而调整检索词或参数；v1、v2、v1b、v2b 的产出原样保留在 `examples/`。
- 不引入第三方依赖（含 requests、pydantic、jsonschema）；不把 Porter 换成 KStem 实现（API 的分词器不公开，近似就是近似，在输出里注明）。
- 不做机器学习式的筛选排序（ASReview 的路线需要标注与 scikit-learn）。

## 8. 调研来源与存档

- 子任务报告原文（主会话存档）：`scratchpad/report_arch.md`、`report_robust.md`、`report_adapt.md`（会话临时目录，不入库）。
- 读过的源码（PyPI sdist / GitHub raw）：CoLRev 0.16.2、search-query 0.15.0、bib-dedupe 0.11.0、findpapers 0.6.7、litstudy 1.0.6、pyalex 0.21、paperfetcher 1.2.2、asreview 3.0.8、openalexR（main）、pybliometrics 4.5、SnowBallSLR（main）；vcrpy、requests-cache、urllib3、tenacity 的相关模块；OpenAlex 文档镜像（ourresearch/docs，已于 2026-08-11 退役）；S2 `graph/v1/swagger.json`。
- 实测记录：`scratchpad/research_robust/live/*.jsonl`（OpenAlex 14、S2 31、Crossref/doi.org 28 个请求，含完整 URL、状态、头、响应摘录）。
- 主会话复核：OpenAlex 未配对引号的静默改写（count 21,344）；`x_query.oqo` 存在；OpenAlex 404 为 HTML；额度头 `X-Ratelimit-Limit: 10000`；英文表头零种子；BOM 读失败；Python 3.9–3.13 测试通过。
- 文献：PRISMA-S（Rethlefsen 等 2021，Systematic Reviews，doi:10.1186/s13643-020-01542-z）。注：主会话给子任务的提示里凭记忆写了错误的 DOI（…01542-5），子任务按规则 2 核对后纠正。

## 9. 实施进度

| 阶段 | 状态 | 说明 |
|---|---|---|
| 0 卫生 | 完成（Step 67） | |
| 1 HTTP 层 | 完成（Step 68） | `--offline` 未单独实现：`--http-mode replay` 即不联网 |
| 2 配置与国际化 | 完成（Step 69–72） | 见下 |
| 3 查询与数据源 | 未开始 | 含 Crossref 适配器（默认关闭，决策点 2） |
| 4 记录、去重、导出、报告 | 未开始 | |
| 5 打包与文档 | 部分提前完成 | GitHub Actions 矩阵已在阶段 2 加入（决策点 4） |

阶段 2 的实现与计划的出入：

- **检索式 id 的格式不进配置**：`Q<数字>` 是 search / merge / qa / compare 之间的文件名约定，不是研究参数；放进配置只会让一处改了、别处读不到文件。
- **`config_hash` 不含 `language` 与 `contact_email`**：两者不影响检索与排序结果，同一配置换语言运行，指纹不变。
- **`--legacy` 不读配置**：它的用途是复现教程 v1、v2，参数固定为前 20 篇、标题至少 5 个词。
- **verify 的结构化结果与展示文字分开**（`novelty_probe/verification.py`）：中文文字与改造前逐字相同（测试与录制件依赖）；英文由同一份结构化结果生成。
- **证据检查接受"注明来源的其他版本"**：本篇无摘要时，判定依据里写明 DOI、且在检索结果中的其他版本的摘要与题目也可作为引文来源（对应 AGENTS.md 的规定）；教程 v2 证据表 rank 3 即属此类。
- **网络护栏**：测试进程与其启动的子进程都拦截非本机连接（`tests/netguard.py`）；护栏的异常继承 BaseException，脚本的 `except Exception` 与 HTTP 客户端的重试都拦不住它。

验收：

- `--lang en` 下帮助、报错、dry-run 汇总、verified 列为英文（`tests/test_config.py`、`tests/test_offline.py`）；
- 英文证据表：导入、检查、生成、核验写回、引文追踪取种子全流程可用（`tests/test_evidence.py`）；
- `evidence check` 抓出非逐字引文、不在检索结果中的 DOI、错误的年份与取值（负对照测试）；两张教程证据表全部通过（Step 70–71）；
- 合并的默认方法在另一个项目目录（`--root`）下重跑，v1b、v2b 的记录与候选表与已提交文件逐字节相同；
- 6 项联网接口检查通过（Step 72）。
