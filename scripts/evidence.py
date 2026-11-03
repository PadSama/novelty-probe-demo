#!/usr/bin/env python3
"""证据表的 JSON 与 Markdown：导入、渲染、检查（novelty_probe/evidence.py）。

JSON（evidence/evidence_table*.json）是数据源，Markdown 是给人看的视图：
  python3 scripts/evidence.py import-md evidence/evidence_table.md     # → evidence/evidence_table.json，并做还原检查
  python3 scripts/evidence.py render evidence/evidence_table.json      # → meta.markdown（默认同名 .md）
  python3 scripts/evidence.py render evidence/evidence_table.json --lang en --out evidence/evidence_table.en.md
  python3 scripts/evidence.py check evidence/evidence_table.json       # 也可直接检查 .md
import-md：表外的文字原样保留，按 JSON 重新生成的 Markdown 与原文件逐字相同（不同时报告哪一行）；
  已有同名 JSON 时，沿用其中同一 DOI 的结构化核验结果（verified 列只由 verify.py 写）。
render：Markdown 在上次导入或渲染之后被手工改过时不覆盖（先 import-md，或加 --force）。
check：取值是否合法、标识符是否来自检索结果（规则 2）、题目 / 年份 / 作者是否与检索结果一致、
  判定依据里引号内的英文是否为摘要（或检索记录的题目）原文。有问题时退出码 1。
  检索结果默认按文件名的后缀推断：evidence_table_v2.* → results/merged/merged_v2.json、evidence/authors_v2.json；
  补充摘要取 evidence/enrichment*.json 全部。不联网。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 novelty_probe 可导入（阶段 5 改为薄壳后去掉）
from novelty_probe import evidence, i18n, runtime
from novelty_probe.i18n import t
from novelty_probe.io import load_json_lenient, read_text, write_json, write_text
from novelty_probe.paths import rel


def suffix_of(path):
    stem = Path(path).stem
    return stem[len("evidence_table"):] if stem.startswith("evidence_table") else ""


def resolve(root, value):
    if value is None:
        return None
    p = Path(value)
    return p if p.is_absolute() else root / p


def main():
    i18n.prepare()
    ap = argparse.ArgumentParser(description="Evidence table: import Markdown, render Markdown, check against retrieval results.")
    ap.add_argument("action", choices=("import-md", "render", "check"), help=t("evidence.arg.action"))
    ap.add_argument("file", type=Path, help=t("evidence.arg.file"))
    ap.add_argument("--out", type=Path, help=t("evidence.arg.out"))
    ap.add_argument("--results", type=Path, help=t("evidence.arg.results"))
    ap.add_argument("--authors", type=Path, help=t("evidence.arg.authors"))
    ap.add_argument("--enrichment", type=Path, nargs="*", help=t("evidence.arg.enrichment"))
    ap.add_argument("--force", action="store_true", help=t("evidence.arg.force"))
    runtime.add_common_args(ap)
    args = ap.parse_args()
    rt = runtime.init(args)
    root, cfg = rt.root, rt.cfg
    suffix = suffix_of(args.file)
    results = args.results or root / "results" / "merged" / f"merged{suffix}.json"
    results = results if results.is_file() else None

    if args.action == "import-md":
        text = read_text(args.file)
        try:
            doc = evidence.import_markdown(text, cfg, source=rel(args.file, root))
        except evidence.EvidenceError as e:
            print(e, file=sys.stderr)
            return 2
        out = args.out or args.file.with_suffix(".json")
        doc["meta"]["markdown"] = rel(args.file, root)
        doc["meta"]["results"] = rel(results, root) if results else None
        if out.is_file():
            try:
                kept = evidence.keep_structured_verification(doc, load_json_lenient(out))
            except ValueError:
                kept = 0
            if kept:
                print(t("evidence.kept_verification", n=kept, path=rel(out, root)))
        again = evidence.render_markdown(doc)
        if again == text:
            print(t("evidence.roundtrip_exact"))
        else:
            a, b = text.split("\n"), again.split("\n")
            diff = [i for i in range(max(len(a), len(b))) if (a[i] if i < len(a) else None) != (b[i] if i < len(b) else None)]
            print(t("evidence.roundtrip_diff", n=len(diff), line=diff[0] + 1))
        write_json(out, doc)
        print(t("evidence.written", path=rel(out, root)))
        return 0

    try:
        doc = evidence.load(args.file, cfg)
    except (evidence.EvidenceError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2

    if args.action == "render":
        own = resolve(root, doc["meta"].get("markdown")) or args.file.with_suffix(".md")
        target = args.out or own
        is_own = target.resolve() == own.resolve()
        if is_own and not args.force and evidence.markdown_was_edited(doc, target):
            print(t("evidence.md_edited", path=rel(target, root)), file=sys.stderr)
            return 2
        text = evidence.render_markdown(doc, args.lang)
        write_text(target, text)
        print(t("evidence.written", path=rel(target, root)))
        if is_own and args.file.suffix.lower() == ".json":
            doc["meta"]["markdown"] = rel(target, root)
            evidence.mark_rendered(doc, text)
            write_json(args.file, doc)
        return 0

    # check
    if args.results is None and doc["meta"].get("results"):
        r = resolve(root, doc["meta"]["results"])
        results = r if r.is_file() else results
    authors = args.authors or root / "evidence" / f"authors{suffix}.json"
    authors = authors if authors.is_file() else None
    enrichment = args.enrichment if args.enrichment is not None else sorted((root / "evidence").glob("enrichment*.json"))
    index = evidence.load_index(results, enrichment, authors) if results else None
    shown = lambda p: rel(p, root) if p else "-"  # noqa: E731
    print(t("evidence.using", results=shown(results), enrichment=", ".join(shown(p) for p in enrichment) or "-",
            authors=shown(authors)))
    if index is None:
        print(t("evidence.no_results"))
    findings = evidence.check(doc, index)
    for level, msg in findings:
        print(f"  {level}: {msg}")
    errors = sum(1 for level, _ in findings if level == "error")
    if not findings:
        print(t("evidence.check_ok", n=len(doc["rows"])))
    else:
        print(t("evidence.check_summary", n=len(doc["rows"]), errors=errors, warnings=len(findings) - errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
