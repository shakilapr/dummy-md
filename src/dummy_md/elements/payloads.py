"""Payload bodies for code, math, and diagram features.

Payloads return construct *content* only: no fences, no delimiters. Renderers own
those characters.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dummy_md.core.context import GenerationContext


@dataclass(frozen=True, slots=True)
class Payload:
    feature_id: str
    language: str
    build: Callable[[GenerationContext], str]


def _python(context: GenerationContext) -> str:
    name = context.text.identifier()
    value = context.text.number(1, 99)
    inner = context.text.identifier(style="camelCase")
    return "\n".join(
        [
            f"def {name}(value: int) -> int:",
            f'    """Return value scaled by {value}."""',
            f"    {inner} = value * {value}",
            f"    return {inner} + {context.text.number(0, 9)}",
            "",
            "",
            'if __name__ == "__main__":',
            f"    print({name}({context.text.number(1, 20)}))",
        ]
    )


def _javascript(context: GenerationContext) -> str:
    name = context.text.identifier(style="camelCase")
    tag = context.text.word()
    threshold = context.text.number(0, 9)
    mapper = "\n".join(
        [
            "    .map((item) => ({",
            "      ...item,",
            f"      tag: '{tag}',",
            "    }));",
        ]
    )
    return "\n".join(
        [
            f"function {name}(items) {{",
            "  return items",
            f"    .filter((item) => item.id > {threshold})",
            mapper,
            "}",
            "",
            f"export default {name};",
        ]
    )


def _bash(context: GenerationContext) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            f'TARGET="{context.text.slug()}"',
            f"RETRIES={context.text.number(1, 5)}",
            "",
            'echo "processing ${TARGET}"',
            'for attempt in $(seq 1 "${RETRIES}"); do',
            '  echo "attempt ${attempt}"',
            "done",
        ]
    )


def _json(context: GenerationContext) -> str:
    return "\n".join(
        [
            "{",
            f'  "id": {context.text.number(1, 999)},',
            f'  "name": "{context.text.word()}",',
            f'  "enabled": {str(context.rng.random() < 0.5).lower()},',
            '  "tags": [',
            f'    "{context.text.word()}",',
            f'    "{context.text.word()}"',
            "  ]",
            "}",
        ]
    )


def _yaml(context: GenerationContext) -> str:
    return "\n".join(
        [
            f"name: {context.text.word()}",
            f"version: {context.text.number(0, 9)}.{context.text.number(0, 9)}",
            "settings:",
            f"  retries: {context.text.number(1, 5)}",
            f"  enabled: {str(context.rng.random() < 0.5).lower()}",
            "tags:",
            f"  - {context.text.word()}",
            f"  - {context.text.word()}",
        ]
    )


def _html(context: GenerationContext) -> str:
    heading = context.text.phrase(min_words=2, max_words=4, title_case=True)
    return "\n".join(
        [
            '<section class="card">',
            f"  <h2>{heading}</h2>",
            f"  <p>{context.text.sentence()}</p>",
            f'  <a href="{context.text.url()}">more</a>',
            "</section>",
        ]
    )


def _sql(context: GenerationContext) -> str:
    table = context.text.identifier(style="snake_case")
    return "\n".join(
        [
            f"SELECT id, {context.text.identifier()} AS label",
            f"FROM {table}",
            f"WHERE created_at >= '{context.text.date()}'",
            "ORDER BY id DESC",
            f"LIMIT {context.text.number(1, 100)};",
        ]
    )


def _diff(context: GenerationContext) -> str:
    return "\n".join(
        [
            f"--- a/{context.text.slug()}.py",
            f"+++ b/{context.text.slug()}.py",
            "@@ -1,3 +1,4 @@",
            f"-def {context.text.identifier()}():",
            f"+def {context.text.identifier()}(value):",
            "     return value",
            "+    # updated",
        ]
    )


def _text(context: GenerationContext) -> str:
    return "\n".join(context.text.sentence() for _ in range(context.text.number(2, 5)))


def _backticks(context: GenerationContext) -> str:
    return "\n".join(
        [
            "```",
            f"inner fence for {context.text.word()}",
            "```",
            f"after {context.text.word()}",
        ]
    )


def _markdown_literal(context: GenerationContext) -> str:
    return "\n".join(
        [
            f"# {context.text.word()}",
            "",
            f"- *{context.text.word()}*",
            f"- `{context.text.word()}`",
            "",
            f"> {context.text.sentence()}",
        ]
    )


CODE_PAYLOADS: tuple[Payload, ...] = (
    Payload("code.payload.python", "python", _python),
    Payload("code.payload.javascript", "javascript", _javascript),
    Payload("code.payload.bash", "bash", _bash),
    Payload("code.payload.json", "json", _json),
    Payload("code.payload.yaml", "yaml", _yaml),
    Payload("code.payload.html", "html", _html),
    Payload("code.payload.sql", "sql", _sql),
    Payload("code.payload.diff", "diff", _diff),
    Payload("code.payload.text", "text", _text),
    Payload("code.payload.backticks", "text", _backticks),
    Payload("code.literal_markdown", "markdown", _markdown_literal),
)

MATH_PAYLOADS: dict[str, Callable[[GenerationContext], str]] = {
    "math.payload.superscript": lambda ctx: (
        f"x^{{{ctx.text.number(2, 9)}}} + y^{{{ctx.text.number(2, 9)}}}"
    ),
    "math.payload.subscript": lambda ctx: (
        f"a_{{{ctx.text.number(1, 9)}}} + b_{{{ctx.text.number(1, 9)}}}"
    ),
    "math.payload.greek": lambda ctx: (
        f"\\alpha + \\beta = \\gamma_{{{ctx.text.number(1, 9)}}}"
    ),
    "math.payload.fractions": lambda ctx: (
        f"\\frac{{{ctx.text.number(1, 9)}}}{{{ctx.text.number(2, 12)}}}"
        f" + \\frac{{1}}{{{ctx.text.number(2, 9)}}}"
    ),
}

MATH_ENVIRONMENTS: dict[str, str] = {
    "math.latex.equation": "equation",
    "math.latex.align": "align",
    "math.latex.gather": "gather",
    "math.latex.cases": "cases",
    "math.latex.matrix": "matrix",
}
