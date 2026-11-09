"""Pandoc-backed fidelity tests.

Substring assertions prove a marker is present; these tests prove a real
Markdown parser interprets the construct as the intended node. They skip when
Pandoc is not installed (it is a developer tool, not a runtime dependency).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, cast

import pytest

from dummy_md import DocumentSpec, ElementRule, Generator, LengthSpec
from dummy_md.core.context import GenerationContext
from dummy_md.elements import (
    ListOptions,
    ParagraphOptions,
    TableOptions,
)
from dummy_md.renderers import get_renderer
from tests.helpers import REGISTRY, build_context, document_of

PANDOC = shutil.which("pandoc")

pytestmark = pytest.mark.skipif(
    PANDOC is None, reason="pandoc is not installed in this environment"
)


def pandoc_ast(text: str) -> dict[str, Any]:
    assert PANDOC is not None
    result = subprocess.run(
        [PANDOC, "-f", "markdown", "-t", "json"],
        input=text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return cast(dict[str, Any], json.loads(result.stdout))


def block_types(ast: dict[str, Any]) -> list[str]:
    return [block["t"] for block in ast["blocks"]]


def inline_types(ast: dict[str, Any]) -> set[str]:
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            kind = node.get("t")
            if isinstance(kind, str):
                found.add(kind)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(ast)
    return found


def render(
    family: str,
    include: tuple[str, ...],
    options: dict[str, ElementRule] | None = None,
) -> str:
    context = build_context(
        dialect="extended", include=include, options=options or {}, seed=3
    )
    block = REGISTRY.generator(family).generate(context)
    return get_renderer(context.dialect).render(document_of(block))


def paragraph_context(feature: str) -> GenerationContext:
    return build_context(
        dialect="extended",
        include=(feature,),
        options={
            "paragraph": ElementRule(
                options=ParagraphOptions(
                    min_sentences=2,
                    max_sentences=2,
                    sentence_min_words=6,
                    sentence_max_words=9,
                    inline_ratio=1.0,
                    emoji_ratio=0.0,
                    block_ratio=0.0,
                )
            )
        },
    )


def test_fenced_div_is_a_div() -> None:
    text = render(
        "paragraph",
        ("paragraph.fenced_div",),
        {"paragraph": ElementRule(options=ParagraphOptions(block_ratio=1.0))},
    )
    ast = pandoc_ast(text)
    assert block_types(ast) == ["Div"]
    assert text.startswith("::: {")


def test_theorem_is_a_div_with_class_and_title() -> None:
    text = render(
        "paragraph",
        ("theorem.block",),
        {"paragraph": ElementRule(options=ParagraphOptions(block_ratio=1.0))},
    )
    ast = pandoc_ast(text)
    assert block_types(ast) == ["Div"]
    attributes = ast["blocks"][0]["c"][0]
    assert "theorem" in attributes[1]
    assert any(key == "title" for key, _ in attributes[2])


def test_definition_list_is_parsed_as_definition_list() -> None:
    text = render(
        "list",
        ("list.definition",),
        {"list": ElementRule(options=ListOptions(definition_ratio=1.0))},
    )
    assert block_types(pandoc_ast(text)) == ["DefinitionList"]


def test_line_block_is_parsed_as_line_block() -> None:
    text = render(
        "paragraph",
        ("paragraph.line_block",),
        {"paragraph": ElementRule(options=ParagraphOptions(block_ratio=1.0))},
    )
    assert block_types(pandoc_ast(text)) == ["LineBlock"]


@pytest.mark.parametrize("style", ["simple", "multiline"])
def test_pandoc_tables_parse_as_tables(style: str) -> None:
    text = render(
        "table",
        (f"table.{style}",),
        {
            "table": ElementRule(
                options=TableOptions(
                    style_ratio=1.0,
                    min_rows=2,
                    max_rows=2,
                    min_columns=2,
                    max_columns=2,
                )
            )
        },
    )
    assert block_types(pandoc_ast(text)) == ["Table"]


@pytest.mark.parametrize("style", ["simple", "multiline"])
def test_tables_with_empty_body_fall_back_to_a_valid_table(style: str) -> None:
    text = render(
        "table",
        (f"table.{style}", "table.header_only"),
        {
            "table": ElementRule(
                options=TableOptions(
                    style_ratio=1.0,
                    header_only_ratio=1.0,
                    min_columns=2,
                    max_columns=2,
                )
            )
        },
    )
    assert block_types(pandoc_ast(text)) == ["Table"]
    if style == "simple":
        assert "|" in text, "an empty simple table must fall back to pipe syntax"


def test_table_caption_is_attached() -> None:
    text = render(
        "table",
        ("table.simple", "table.caption"),
        {
            "table": ElementRule(
                options=TableOptions(
                    style_ratio=1.0,
                    caption_ratio=1.0,
                    min_rows=2,
                    max_rows=2,
                )
            )
        },
    )
    ast = pandoc_ast(text)
    assert block_types(ast) == ["Table"]
    caption = ast["blocks"][0]["c"][1]
    assert caption[1], "caption content should be attached to the table"


def test_figure_is_parsed_as_figure() -> None:
    text = render(
        "image",
        ("image.figure.caption", "image.figure.label"),
        {"image": ElementRule(options={"figure_ratio": 1.0})},
    )
    assert block_types(pandoc_ast(text)) == ["Figure"]


@pytest.mark.parametrize(
    ("feature", "expected"),
    [
        ("inline.superscript", "Superscript"),
        ("inline.subscript", "Subscript"),
        ("inline.small_caps", "SmallCaps"),
    ],
)
def test_typography_parses_as_inline_nodes(feature: str, expected: str) -> None:
    context = paragraph_context(feature)
    block = REGISTRY.generator("paragraph").generate(context)
    text = get_renderer(context.dialect).render(document_of(block))
    assert expected in inline_types(pandoc_ast(text))


@pytest.mark.parametrize(
    ("feature", "pandoc_style"),
    [
        ("list.ordered.alpha", "LowerAlpha"),
        ("list.ordered.roman", "LowerRoman"),
        ("list.example_numbered", "Example"),
    ],
)
def test_ordered_list_styles_parse(feature: str, pandoc_style: str) -> None:
    text = render("list", (feature,))
    ast = pandoc_ast(text)
    assert block_types(ast) == ["OrderedList"]
    attributes = ast["blocks"][0]["c"][0]
    assert attributes[1]["t"] == pandoc_style


def test_figure_with_size_keeps_a_single_attribute_block() -> None:
    context = build_context(
        dialect="extended",
        include=(
            "image.figure.caption",
            "image.figure.label",
            "image.width",
            "image.height",
        ),
        options={
            "image": ElementRule(options={"figure_ratio": 1.0, "size_ratio": 1.0})
        },
    )
    block = REGISTRY.generator("image").generate(context)
    text = get_renderer(context.dialect).render(document_of(block))
    assert text.count("{") == 1, "size and label attributes must share one block"
    assert "}{" not in text
    assert "#fig:" in text and "width=" in text


def test_math_label_survives_into_math_content() -> None:
    context = build_context(
        dialect="extended",
        include=("math.display.dollar", "math.label"),
        options={"math": ElementRule(options={"label_ratio": 1.0})},
    )
    block = REGISTRY.generator("math").generate(context)
    text = get_renderer(context.dialect).render(document_of(block))
    ast = pandoc_ast(text)
    serialized = json.dumps(ast)
    assert "\\\\label{eq:" in serialized


def test_generated_extended_document_has_no_malformed_blocks() -> None:
    spec = DocumentSpec(
        dialect="extended",
        seed=11,
        length=LengthSpec(12_000),
        include=[
            "heading.*",
            "paragraph.*",
            "list.*",
            "table.*",
            "blockquote.*",
            "math.*",
            "diagram.*",
            "html.*",
            "inline.*",
            "link.*",
            "image.*",
        ],
    )
    text = Generator(spec).generate()
    ast = pandoc_ast(text)
    types = set(block_types(ast))
    # A fenced div left unparsed shows up as a paragraph starting with ":::".
    for block in ast["blocks"]:
        if block["t"] == "Para":
            content = json.dumps(block)
            assert "::: {" not in content
    assert types <= {
        "Para",
        "Header",
        "BulletList",
        "OrderedList",
        "DefinitionList",
        "LineBlock",
        "CodeBlock",
        "BlockQuote",
        "Table",
        "Div",
        "Figure",
        "HorizontalRule",
        "RawBlock",
        "Plain",
    }
