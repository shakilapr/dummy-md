from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from dummy_md.core.nodes import (
    Blockquote,
    CodeBlock,
    Document,
    Emphasis,
    FootnoteDefinition,
    Heading,
    Image,
    Link,
    ListBlock,
    ListItem,
    Paragraph,
    Table,
    TableCell,
    Text,
    children_of,
    text_content,
    walk,
)


def test_heading_level_bounds() -> None:
    with pytest.raises(ValueError, match="level"):
        Heading(level=0)
    with pytest.raises(ValueError, match="level"):
        Heading(level=7)


def test_setext_limited_to_two_levels() -> None:
    Heading(level=2, style="setext")
    with pytest.raises(ValueError, match="setext"):
        Heading(level=3, style="setext")


def test_document_rejects_inline_children() -> None:
    with pytest.raises(TypeError, match="BlockNode"):
        Document(children=(Text("loose inline"),))  # type: ignore[arg-type]


def test_list_delimiter_validation() -> None:
    ListBlock(ordered=True, delimiter=".")
    ListBlock(ordered=False, delimiter="*")
    with pytest.raises(ValueError, match="delimiter"):
        ListBlock(ordered=True, delimiter="-")
    with pytest.raises(ValueError, match="delimiter"):
        ListBlock(ordered=False, delimiter="1")


def test_indented_code_rejects_info() -> None:
    with pytest.raises(ValueError, match="info"):
        CodeBlock(code="x = 1", indented=True, info="python")


def test_table_alignment_count() -> None:
    cell = TableCell(children=(Text("h"),))
    with pytest.raises(ValueError, match="alignment"):
        Table(header=(cell,), alignments=("left", "right"))


def test_nodes_are_immutable_and_comparable() -> None:
    first = Paragraph(children=(Text("hello"),))
    second = Paragraph(children=(Text("hello"),))
    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.children = ()  # type: ignore[misc]


def test_walk_visits_nested_blocks() -> None:
    doc = Document(
        children=(
            Heading(level=1, children=(Text("Title"),)),
            Blockquote(children=(Paragraph(children=(Text("quoted"),)),)),
            ListBlock(
                items=(ListItem(children=(Paragraph(children=(Text("item"),)),)),)
            ),
        )
    )
    nodes = walk(doc)
    texts = [n.content for n in nodes if isinstance(n, Text)]
    assert texts == ["Title", "quoted", "item"]


def test_walk_reaches_table_cells_and_images() -> None:
    cell = TableCell(children=(Image(alt=(Text("alt"),)),))
    table = Table(header=(cell,), rows=(), alignments=("left",))
    nodes = walk(table)
    assert sum(isinstance(n, Text) for n in nodes) == 1


def test_children_of_inline_containers() -> None:
    emphasis = Emphasis(children=(Text("a"), Link(children=(Text("b"),))))
    assert len(children_of(emphasis)) == 2


def test_text_content_ignores_markup() -> None:
    inlines = (Text("alpha "), Emphasis(children=(Text("beta"),)), Text(" gamma"))
    assert text_content(inlines) == "alpha beta gamma"


def test_footnote_definitions_are_nodes() -> None:
    definition = FootnoteDefinition(
        label="1", children=(Paragraph(children=(Text("note"),)),)
    )
    assert len(children_of(definition)) == 1


def test_list_style_validation() -> None:
    with pytest.raises(ValueError, match="requires an ordered list"):
        ListBlock(style="alpha")
    with pytest.raises(ValueError, match="unknown list style"):
        ListBlock(ordered=True, style="greek")  # type: ignore[arg-type]
    assert ListBlock(ordered=True, style="alpha").style == "alpha"


def test_table_style_validation() -> None:
    with pytest.raises(ValueError, match="unknown table style"):
        Table(style="fancy")  # type: ignore[arg-type]
    assert Table(style="grid").style == "grid"
