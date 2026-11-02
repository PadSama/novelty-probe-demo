"""novelty-probe 的核心层（纯标准库，Python 3.9+）。

scripts/ 下的命令脚本调用这里的模块。阶段 0（2026-11-02）只包含文件读写与路径工具；
后续阶段加入 HTTP 客户端、配置、查询 AST、数据源适配器等，见 docs/ARCHITECTURE_REVIEW.md 第 4–5 节。
"""
__version__ = "0.2.0.dev0"
SCHEMA_VERSION = 1
