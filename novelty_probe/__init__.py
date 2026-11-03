"""novelty-probe：围绕研究想法查找文献证据的命令行工具（纯标准库，Python 3.9+）。

命令：novelty-probe <命令>（入口 cli.py，各命令在 commands/）；共用的模块：检索式语法树（query）、数据源（sources/）、
HTTP 客户端与缓存（http、cache）、配置（config）、界面语言（i18n）、证据表（evidence、verification）、文本匹配（text）、
合并记录与去重（record、dedupe、rank）、导出与报告（export、report）。新项目的文档模板在 templates/。
设计与演进见源码仓库的 docs/ARCHITECTURE_REVIEW.md、docs/ROADMAP.md。
"""
__version__ = "2.0.0"
SCHEMA_VERSION = 1
