#!/usr/bin/env python3
"""查看与检查项目配置 novelty-probe.json（novelty_probe/config.py）。

  python3 scripts/config.py show           打印有效配置（内置默认值 + 配置文件），以及来源文件与 config_hash
  python3 scripts/config.py show --diff    只打印与内置默认值不同的部分
  python3 scripts/config.py check          只检查：有问题时列出全部问题，退出码 2
  python3 scripts/config.py init           在项目根目录写一个最小的 novelty-probe.json（已存在时不覆盖）

通用参数 --root / --config / --lang 与其他脚本相同。不联网。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe import config as np_config, i18n, runtime
from novelty_probe.i18n import tr
from novelty_probe.io import dump_json, write_text
from novelty_probe.paths import rel


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Show, check or create the project config (novelty-probe.json).")
    ap.add_argument("action", choices=("show", "check", "init"))
    ap.add_argument("--diff", action="store_true", help=tr("show 时只打印与内置默认值不同的部分", "With show: print only what differs from the defaults"))
    runtime.add_common_args(ap)
    args = ap.parse_args()
    if args.action == "init":
        root = runtime.find_root(args.root)
        target = Path(args.config) if args.config else root / np_config.CONFIG_NAME
        if target.exists():
            print(tr("{f} 已存在，未改动", "{f} already exists; left unchanged", f=rel(target, root)))
            return 1
        write_text(target, dump_json(np_config.STARTER))
        print(tr("已写入：{f}", "written: {f}", f=rel(target, root)))
        return 0
    rt = runtime.init(args)   # 配置有问题时在这里以退出码 2 结束，并列出全部问题
    cfg = rt.cfg
    source = rel(cfg.file, rt.root) if cfg.file else tr("（无配置文件，只用内置默认值）", "(no config file; built-in defaults only)")
    print(tr("配置文件：{s}", "config file: {s}", s=source), file=sys.stderr)
    print(f"config_hash: {cfg.hash}", file=sys.stderr)
    if args.action == "check":
        print(tr("检查通过", "OK"))
        return 0
    print(json.dumps(np_config.diff(cfg) if args.diff else dict(cfg), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
