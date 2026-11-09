"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import dummy_md
from dummy_md.core.budget import Unit
from dummy_md.core.catalog import CATALOG
from dummy_md.core.dialects import DIALECTS
from dummy_md.exceptions import DummyMdError

PROGRAM = "dummy-md"

_SIZE_SUFFIXES: dict[str, int] = {"KB": 1000, "MB": 1000**2, "GB": 1000**3}


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except DummyMdError as error:
        print(f"{PROGRAM}: error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"{PROGRAM}: error: {error}", file=sys.stderr)
        return 1


# -- parser ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Generate syntactically valid Markdown placeholder documents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="generate a document")
    amount = generate.add_mutually_exclusive_group()
    amount.add_argument("--chars", type=int, metavar="N", help="target characters")
    amount.add_argument("--words", type=int, metavar="N", help="target words")
    amount.add_argument("--lines", type=int, metavar="N", help="target lines")
    amount.add_argument("--blocks", type=int, metavar="N", help="top-level blocks")
    amount.add_argument("--bytes", metavar="N", help="target UTF-8 size, e.g. 50MB")
    generate.add_argument("--dialect", default="gfm", help="dialect name")
    generate.add_argument(
        "--preset", default=None, help="built-in preset (default, readme, tables, ...)"
    )
    generate.add_argument("--seed", type=int, default=0, help="random seed")
    generate.add_argument(
        "--text", default="pseudowords", help="text style (pseudowords, lorem, tokens)"
    )
    generate.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help="feature pattern to include (repeatable)",
    )
    generate.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="feature pattern to exclude (repeatable)",
    )
    generate.add_argument(
        "--exact", action="store_true", help="require the exact requested length"
    )
    generate.add_argument(
        "--tolerance",
        type=float,
        default=0.05,
        help="approximate-mode tolerance (default 0.05)",
    )
    generate.add_argument("--depth", type=int, default=3, help="maximum nesting depth")
    generate.add_argument(
        "-o", "--output", default=None, metavar="PATH", help="write to a file"
    )

    elements = subparsers.add_parser("elements", help="list feature ids")
    elements.add_argument("--dialect", default=None, help="filter by dialect")
    elements.add_argument(
        "--all", action="store_true", help="include planned but unimplemented features"
    )

    subparsers.add_parser("dialects", help="list dialects")
    subparsers.add_parser("presets", help="list presets")

    validate = subparsers.add_parser("validate", help="validate a Markdown file")
    validate.add_argument("path", help="file to validate")
    validate.add_argument("--dialect", default="gfm", help="dialect name")

    return parser


# -- dispatch ----------------------------------------------------------------
def _dispatch(args: argparse.Namespace) -> int:
    command = args.command
    if command == "generate":
        return _generate(args)
    if command == "elements":
        return _elements(args)
    if command == "dialects":
        return _dialects()
    if command == "presets":
        return _presets()
    if command == "validate":
        return _validate(args)
    raise AssertionError(f"unhandled command {command!r}")


def _generate(args: argparse.Namespace) -> int:
    length, unit = _amount(args)
    text = dummy_md.generate(
        length=length,
        unit=unit,
        dialect=args.dialect,
        seed=args.seed,
        include=tuple(args.include),
        exclude=tuple(args.exclude),
        text_style=args.text,
        max_nesting_depth=args.depth,
        mode="exact" if args.exact else "approximate",
        tolerance=args.tolerance,
        preset=args.preset,
    )
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 0


def _amount(args: argparse.Namespace) -> tuple[int, Unit]:
    if args.bytes is not None:
        return parse_size(args.bytes), "bytes"
    if args.words is not None:
        return args.words, "words"
    if args.lines is not None:
        return args.lines, "lines"
    if args.blocks is not None:
        return args.blocks, "blocks"
    return args.chars if args.chars is not None else 1000, "chars"


def parse_size(value: str) -> int:
    """Parse ``500``, ``50KB``, ``50 MB`` or ``1.5MB`` into bytes."""
    text = value.strip().upper().replace(" ", "")
    for suffix, multiplier in _SIZE_SUFFIXES.items():
        if text.endswith(suffix):
            number = text[: -len(suffix)]
            try:
                return int(float(number) * multiplier)
            except ValueError as error:
                raise DummyMdError(f"invalid size {value!r}") from error
    try:
        return int(text)
    except ValueError as error:
        raise DummyMdError(f"invalid size {value!r}") from error


def _elements(args: argparse.Namespace) -> int:
    if args.all:
        for spec in sorted(CATALOG, key=lambda item: item.id):
            mark = "" if spec.implemented else "  (planned)"
            print(f"{spec.id}{mark}")
        return 0
    for feature_id in dummy_md.available_elements(args.dialect):
        print(feature_id)
    return 0


def _dialects() -> int:
    for name in dummy_md.available_dialects():
        print(f"{name}\t{len(DIALECTS[name].features)} features")
    return 0


def _presets() -> int:
    for name, description in dummy_md.available_presets().items():
        print(f"{name}\t{description}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    text = Path(args.path).read_text(encoding="utf-8")
    report = dummy_md.validate(text, args.dialect)
    if report.ok:
        print(f"ok\t{report.tokens} tokens\t{args.path}")
        return 0
    for error in report.errors:
        print(f"{PROGRAM}: error: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
