"""Command line interface for tds-parser."""
from __future__ import annotations

import argparse
import sys

from .extract import extract_text
from .parse import parse_text, to_csv, to_json, to_markdown


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="tds-parse",
        description="从塑料物性表（TDS）PDF/文本中提取结构化物性数据。",
    )
    ap.add_argument("source", help="TDS 文件路径（.pdf 或纯文本）")
    ap.add_argument(
        "-f", "--format", choices=("json", "md", "csv"), default="json",
        help="输出格式（默认 json）",
    )
    ap.add_argument("-o", "--out", help="输出文件（默认打印到标准输出）")
    ap.add_argument(
        "--text", action="store_true", help="把 source 当作纯文本而不是 PDF 解析",
    )
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.text:
        with open(args.source, encoding="utf-8") as fh:
            text, pages = fh.read(), 0
    else:
        text, pages = extract_text(args.source)

    props = parse_text(text)
    if args.format == "json":
        out = to_json(props, source=args.source, pages=pages)
    elif args.format == "md":
        out = to_markdown(props)
    else:
        out = to_csv(props)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"已写入 {args.out}（{len(props)} 条物性，其中 "
              f"{sum(1 for p in props if p.key)} 条已识别）", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
