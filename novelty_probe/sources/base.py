"""数据源协议。每个数据源一个模块，实现 Source 的方法，在 sources/__init__.py 的 REGISTRY 中登记；
search.py、merge.py、qa.py、compare.py 从注册表取数据源与文件名前缀，加一个数据源不用改它们。"""
from dataclasses import dataclass, field


@dataclass
class Context:
    """一次检索所需的运行环境（由 search.py 组装）。"""
    fetch: object                  # fetch(url) -> JSON；search.py 传入自己的 get_json（测试可替换）
    client: object                 # novelty_probe.http.Client（翻页、断点）
    truncation: dict = field(default_factory=dict)   # 截断词 → 完整词（配置 queries.truncation）
    top_n: int = 25                # 保存的条数
    max_records: int = 0           # 需要本地重排的来源最多取回多少条
    checkpoint: object = None      # 翻页断点文件


class Source:
    name = ""              # 文件名前缀（{name}_Q1.json）与 meta.source_api
    conversion = ""        # 写进 meta.conversion；合并时据此检查同一来源是否混有不同的检索方式，改动即视为新方法
    paginates = False      # 是否翻页（翻页的来源有断点文件）
    default_max_records = 0
    enabled_by_default = True   # 配置 sources.<name>.enabled 没写时是否启用
    # 各项写法在哪里实现：api（数据源原生支持）、expand（截断词换成完整词）、local（取回后在本地按标题与摘要判断）
    capabilities = {}
    # 检索报告（novelty_probe/report.py）"数据库与接口"一节的写法：显示名、接口、排序（中文, 英文）
    label = ""
    interface = ""
    ranking = ("", "")
    # 检索报告"数据来源与条款"一节的写法（中文, 英文）：数据的许可与公开使用时的署名要求
    attribution = ("", "")

    def serialize(self, query, truncation):
        """语法树 → 发给数据源的检索串（不合要求时抛 QueryError，错误码 Q2xx）。"""
        raise NotImplementedError

    def unsupported(self, query):
        """该数据源无法实现的写法（每项一句说明）；非空时 dry-run 打印 SKIPPED，检索时跳过这条检索式。"""
        return []

    def plan(self, top_n, max_records):
        """每条检索式最多发多少个请求、每个请求的 OpenAlex 额度（dry-run 的请求估算）。"""
        return {"requests": 1, "credits_per_request": 0}

    def search(self, item, year_from, ctx):
        """执行一条检索式（item：{"id", "query", "purpose"}），返回 (meta, records)。"""
        raise NotImplementedError
