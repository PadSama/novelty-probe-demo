"""各命令的实现：novelty-probe <命令> 运行这里的 <命令>.py 的 main()（命令表见 novelty_probe/cli.py）。

每个模块保留原来 scripts/<命令>.py 的模块级常量（ROOT、RAW_DIR 等），在其他项目目录运行时由 runtime.bind_root 换成该目录；
测试可以照旧替换这些常量。"""
