"""各命令脚本共用的启动步骤：命令行参数、项目根目录、配置、界面语言、HTTP 客户端、控制台编码。

用法（脚本里）：
    ap = argparse.ArgumentParser(...)
    runtime.add_common_args(ap, network=True)
    args = ap.parse_args()
    rt = runtime.init(args)          # rt.root, rt.cfg, rt.client, rt.lang
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from . import config as config_mod
from . import i18n
from .http import POLICIES, Client, HostPolicy, add_http_args, set_default_client
from .io import configure_console
from .paths import find_root  # noqa: F401  （scripts/config.py 经由 runtime 使用）


@dataclass
class Runtime:
    root: object
    cfg: object
    client: object
    lang: str


def bind_root(g, root, layout):
    """把脚本模块里的路径常量换到另一个项目根目录。
    g：脚本的 globals()；layout：{常量名: 相对于项目根目录的路径}。
    只有 root 与脚本所在的仓库不同时才改：在仓库里运行（含测试）时什么都不变，测试可以照旧替换这些常量。"""
    script_root = Path(g["__file__"]).resolve().parent.parent
    root = Path(root).resolve()
    if root == script_root:
        return False
    g["ROOT"] = root
    for name, relpath in layout.items():
        g[name] = root / relpath
    return True


def add_common_args(ap, network=False):
    g = ap.add_argument_group("project")
    g.add_argument("--root", default=None, help=i18n.t("arg.root"))
    g.add_argument("--config", default=None, help=i18n.t("arg.config"))
    g.add_argument("--lang", choices=("zh", "en"), default=None, help=i18n.t("arg.lang"))
    if network:
        add_http_args(ap)
    return g


def policies_from_config(cfg):
    """配置里的 http.policies 覆盖默认的按主机策略。"""
    out = dict(POLICIES)
    for host, over in ((cfg.get("http") or {}).get("policies") or {}).items():
        base = POLICIES.get(host, HostPolicy())
        fields = {k: v for k, v in vars(base).items()}
        unknown = set(over) - set(fields)
        if unknown:
            raise config_mod.ConfigError(i18n.tr("http.policies.{h} 中有未知参数：{u}", "unknown parameters in http.policies.{h}: {u}",
                                                 h=host, u=sorted(unknown)))
        fields.update(over)
        out[host] = HostPolicy(**fields)
    return out


def user_agent(cfg):
    """默认是通用的客户端名；只有研究者在配置里填了 contact_email 时才附上 mailto（Crossref 礼貌池）。"""
    from . import __version__
    email = (cfg.get("contact_email") or "").strip()
    base = f"novelty-probe/{__version__} (+https://github.com/PadSama/novelty-probe-demo"
    return f"{base}; mailto:{email})" if email else base + ")"


def init(args, network=None):
    """解析通用参数，返回 Runtime。配置有误时以退出码 2 结束并列出问题。"""
    configure_console()
    root = find_root(getattr(args, "root", None))
    try:
        cfg = config_mod.load_config(getattr(args, "config", None), root=root)
    except config_mod.ConfigError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
    lang = getattr(args, "lang", None) or os.environ.get("NP_LANG") or cfg.get("language") or "zh"
    i18n.set_language(lang)
    for w in cfg.warnings:
        print(i18n.tr("配置警告：{w}", "config warning: {w}", w=w), file=sys.stderr)
    client = None
    if network or (network is None and hasattr(args, "http_mode")):
        try:
            client = Client(getattr(args, "http_mode", None), cache_dir=getattr(args, "cache_dir", None),
                            cassette=getattr(args, "cassette", None), policies=policies_from_config(cfg),
                            user_agent=user_agent(cfg))
        except (ValueError, config_mod.ConfigError) as e:
            print(e, file=sys.stderr)
            sys.exit(2)
        client.refresh = bool(getattr(args, "refresh", False))
        set_default_client(client)
    return Runtime(root=root, cfg=cfg, client=client, lang=lang)
