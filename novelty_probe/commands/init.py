#!/usr/bin/env python3
"""新建项目目录：novelty-probe init [目录] [--update-docs]

写入（已有的文件一律不覆盖）：
  PROJECT.md          助手的角色与三条硬规则
  AGENTS.md           给 AI 编程助手的说明
  HOWTO.md            操作指南（T1–T6 的命令与提示词）
  idea/idea.md        研究想法（由研究者填写；模板里只有填写说明）
  novelty-probe.json  项目配置（只写与内置默认值不同的设置）
  logs/RUN_LOG.md     运行日志（Step 0 记下本次新建）
  .gitignore          忽略 HTTP 缓存
以及空目录 facets/、queries/、results/raw/、results/merged/、evidence/。
三份文档取自安装的 novelty-probe（novelty_probe/templates/）；工具升级后用 --update-docs 只刷新这三份文档。
研究想法与检索结果留在这个目录里：不要放进 novelty-probe 的源码仓库（默认拒绝，--force 可以越过）。
"""
import argparse
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

from novelty_probe import __version__, i18n
from novelty_probe import config as np_config
from novelty_probe.commands.logrun import next_step
from novelty_probe.i18n import tr
from novelty_probe.io import append_text, configure_console, dump_json, write_text
from novelty_probe.paths import MARKERS, PACKAGE_ROOT

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
DOCS = ("PROJECT.md", "AGENTS.md", "HOWTO.md")
DIRS = ("idea", "facets", "queries", "results/raw", "results/merged", "evidence", "logs")
LOG_HEADER = ("# RUN_LOG\n\n> 只追加，不改写。每条记录：时间 / 步骤 / 命令 / 产出文件。\n",
              "# RUN_LOG\n\n> Append only; never rewrite an entry. Each entry: time / step / command / output files.\n")


def project_files():
    """相对路径 → 内容（新建项目时写入的文件，日志另写）。"""
    files = {doc: (TEMPLATES / doc).read_text(encoding="utf-8") for doc in DOCS}
    files["idea/idea.md"] = (TEMPLATES / "idea.md").read_text(encoding="utf-8")
    files["novelty-probe.json"] = dump_json(np_config.STARTER)
    files[".gitignore"] = (TEMPLATES / "gitignore.txt").read_text(encoding="utf-8")
    return files


def inside_source_repo(target):
    """target 在 novelty-probe 的源码仓库里（不是仓库根目录本身）：研究数据会混进工具的代码仓库。"""
    repo = PACKAGE_ROOT
    return (repo / "pyproject.toml").is_file() and target != repo and repo in target.parents


def log_entry(step, title, command, created, updated, kept):
    """运行日志的一条（格式与手写条目相同；语言随界面语言）。"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    what = tr("新建项目目录。" if step == 0 else "补齐缺少的文件或刷新文档。",
              "Created the project folder." if step == 0 else "Added missing files or refreshed the docs.")
    if kept:
        what += tr("已有的文件未改动：{k}。", " Existing files left unchanged: {k}.",
                   k=tr("、", ", ").join(f"`{k}`" for k in kept))
    lines = [f"\n---\n\n## [{now}] Step {step} — {title}\n", tr("**命令**", "**Command**") + "\n",
             f"```bash\n{command}\n```\n", tr("**做了什么**：novelty-probe {v}。", "**What was done**: novelty-probe {v}. ",
                                                v=__version__) + what + "\n"]
    if created or updated:
        lines.append(tr("**产出文件**", "**Output files**") + "\n")
        lines += [tr("- `{f}`（新建）", "- `{f}` (created)", f=f) for f in created]
        lines += [tr("- `{f}`（刷新为 novelty-probe {v} 的版本）", "- `{f}` (refreshed to the novelty-probe {v} version)",
                     f=f, v=__version__) for f in updated]
        lines.append("")
    lines.append(tr("**备注**：本步未执行任何文献检索。", "**Note**: no literature search was run in this step.") + "\n")
    return "\n".join(lines)


def main():
    i18n.prepare()
    configure_console()
    ap = argparse.ArgumentParser(description="Create a novelty-probe project folder (existing files are never overwritten).")
    ap.add_argument("folder", nargs="?", default=".", help=tr("项目目录（默认当前目录；不存在时新建）",
                                                              "Project folder (default: current folder; created if missing)"))
    ap.add_argument("--update-docs", action="store_true",
                    help=tr("只把 PROJECT.md、AGENTS.md、HOWTO.md 刷新为当前版本（工具升级后用）",
                            "Refresh only PROJECT.md, AGENTS.md and HOWTO.md to this version (after upgrading the tool)"))
    ap.add_argument("--force", action="store_true",
                    help=tr("允许在 novelty-probe 的源码仓库里新建项目", "Allow a project inside the novelty-probe source repository"))
    ap.add_argument("--lang", choices=("zh", "en"), default=None, help=i18n.t("arg.lang"))
    args = ap.parse_args()
    if args.lang:
        i18n.set_language(args.lang)
    target = Path(args.folder).resolve()
    if inside_source_repo(target) and not args.force:
        print(tr("{d} 在 novelty-probe 的源码仓库里：研究想法与检索结果会混进工具的代码仓库（公开仓库时会被一起推送）。"
                 "请换一个仓库之外的目录；确实要这样做时加 --force。",
                 "{d} is inside the novelty-probe source repository, so your idea and results would mix with the tool's code "
                 "(and be pushed with it if the repository is public). Use a folder outside the repository, or add --force.",
                 d=target), file=sys.stderr)
        return 2
    if target.is_file():
        print(tr("{d} 是一个文件，不是目录", "{d} is a file, not a folder", d=target), file=sys.stderr)
        return 2
    is_project = any((target / m).is_file() for m in MARKERS)
    for d in DIRS:
        (target / d).mkdir(parents=True, exist_ok=True)
    created, updated, kept = [], [], []
    for rel, text in project_files().items():
        path = target / rel
        if not path.exists():
            write_text(path, text)
            created.append(rel)
        elif args.update_docs and rel in DOCS and path.read_text(encoding="utf-8") != text:
            write_text(path, text)
            updated.append(rel)
        else:
            kept.append(rel)
    log = target / "logs" / "RUN_LOG.md"
    new_log = not log.exists()
    if new_log:
        write_text(log, tr(*LOG_HEADER))
        created.append("logs/RUN_LOG.md")
    shown = ["novelty-probe", "init", target.name or "."] + (["--update-docs"] if args.update_docs else [])
    step = 0 if new_log else next_step(log)
    if step == 0:
        title = tr("新建项目（novelty-probe init）", "Create the project (novelty-probe init)")
    elif args.update_docs:
        title = tr("刷新文档（novelty-probe init --update-docs）", "Refresh the docs (novelty-probe init --update-docs)")
    else:
        title = tr("补齐项目文件（novelty-probe init）", "Add missing project files (novelty-probe init)")
    if created or updated or step == 0:
        append_text(log, log_entry(step, title, shlex.join(shown), created, updated, kept))

    for f in created:
        print(tr("新建  {f}", "created  {f}", f=f))
    for f in updated:
        print(tr("刷新  {f}", "updated  {f}", f=f))
    for f in kept:
        print(tr("保留  {f}（已存在，未改动）", "kept     {f} (exists; unchanged)", f=f))
    if not is_project:
        print()
        print(tr("项目目录：{d}", "project folder: {d}", d=target))
        print(tr("下一步：1）在 idea/idea.md 写下研究想法；2）在这个目录里启动 AI 编程助手，让它先读 AGENTS.md，"
                 "再按 HOWTO.md 第 3 节写检索式；3）运行 novelty-probe run。",
                 "Next: 1) write your idea in idea/idea.md; 2) start your AI coding assistant in this folder, have it read "
                 "AGENTS.md, then write the queries as in HOWTO.md section 3; 3) run novelty-probe run."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
