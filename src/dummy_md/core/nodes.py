"""Typed Markdown AST.

Generators build these immutable nodes; renderers turn them into characters.
No other layer is allowed to emit Markdown syntax.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar

Alignment = Literal["left", "center", "right", "default"]
CodeSpanStyle = Literal["emphasis"]  # reserved for future inline variants
EmphasisLevel = Literal[1, 2, 3]
HeadingStyle = Literal["atx", "setext"]
InlineKind = Literal["inline", "full", "collapsed", "shortcut"]
LineBreakStyle = Literal["spaces", "backslash", "soft"]
MathDelimiter = Literal["dollar", "bracket"]
ReferenceKind = Literal["named", "decimal", "hex"]
ReferenceTitleDelimiter = Literal['"', "'", "("]

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class MarkdownNode:
    """Root of the node hierarchy."""

    __slots__ = ()

    def accept(self, visitor: Visitor[T]) -> T:
        return visitor.visit(self)


class Visitor(Protocol[T_co]):
    """A single-method visitor used by :meth:`MarkdownNode.accept`."""

    def visit(self, node: MarkdownNode) -> T_co: ...


class BlockNode(MarkdownNode):
    """A node that occupies its own block in the document flow."""

    __slots__ = ()


class InlineNode(MarkdownNode):
    """A node that lives inside a block's inline sequence."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Attributes:
    """Pandoc-style `{#id .class key=value}` attributes."""

    identifier: str | None = None
    classes: tuple[str, ...] = ()
    pairs: tuple[tuple[str, str], ...] = ()

    def is_empty(self) -> bool:
        return not (self.identifier or self.classes or self.pairs)


# --------------------------------------------------------------------------
# Block nodes
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Document(BlockNode):
    children: tuple[BlockNode, ...] = ()
    link_definitions: tuple[LinkDefinition, ...] = ()
    footnote_definitions: tuple[FootnoteDefinition, ...] = ()

    def __post_init__(self) -> None:
        for child in self.children:
            if not isinstance(child, BlockNode):
                raise TypeError(
                    f"Document children must be BlockNode, got {type(child).__name__}"
                )


@dataclass(frozen=True, slots=True)
class Heading(BlockNode):
    level: int
    children: tuple[InlineNode, ...] = ()
    style: HeadingStyle = "atx"
    closed: bool = False
    attributes: Attributes | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 6:
            raise ValueError(f"heading level must be 1..6, got {self.level}")
        if self.style == "setext" and self.level > 2:
            raise ValueError("setext headings only support levels 1 and 2")


@dataclass(frozen=True, slots=True)
class Paragraph(BlockNode):
    children: tuple[InlineNode, ...] = ()


@dataclass(frozen=True, slots=True)
class ThematicBreak(BlockNode):
    character: Literal["-", "*", "_"] = "-"
    spacing: int = 0


@dataclass(frozen=True, slots=True)
class CodeBlock(BlockNode):
    code: str
    info: str = ""
    fence_char: Literal["`", "~"] = "`"
    fence_length: int = 0
    indented: bool = False
    attributes: Attributes | None = None
    caption: str = ""

    def __post_init__(self) -> None:
        if self.indented and self.info:
            raise ValueError("indented code blocks cannot carry an info string")
        if self.fence_length and self.fence_length < 3:
            raise ValueError("fence_length must be at least 3 when specified")


@dataclass(frozen=True, slots=True)
class HTMLBlock(BlockNode):
    block_type: int
    content: str

    def __post_init__(self) -> None:
        if not 1 <= self.block_type <= 7:
            raise ValueError(f"HTML block type must be 1..7, got {self.block_type}")


@dataclass(frozen=True, slots=True)
class ListBlock(BlockNode):
    ordered: bool = False
    items: tuple[ListItem, ...] = ()
    delimiter: str = "-"
    start: int = 1
    tight: bool = True

    def __post_init__(self) -> None:
        if self.ordered and self.delimiter not in {".", ")"}:
            raise ValueError(
                f"ordered list delimiter must be '.' or ')', got {self.delimiter!r}"
            )
        if not self.ordered and self.delimiter not in {"-", "*", "+"}:
            raise ValueError(
                f"bullet delimiter must be '-', '*' or '+', got {self.delimiter!r}"
            )
        if self.ordered and self.start < 0:
            raise ValueError("ordered list start must be non-negative")


@dataclass(frozen=True, slots=True)
class ListItem(BlockNode):
    children: tuple[BlockNode, ...] = ()
    checked: bool | None = None


@dataclass(frozen=True, slots=True)
class Blockquote(BlockNode):
    children: tuple[BlockNode, ...] = ()


@dataclass(frozen=True, slots=True)
class Callout(BlockNode):
    kind: str
    title: str = ""
    children: tuple[BlockNode, ...] = ()
    foldable: bool = False
    collapsed: bool = False

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("callout kind must not be empty")
        if self.collapsed and not self.foldable:
            raise ValueError("collapsed callouts must be foldable")


@dataclass(frozen=True, slots=True)
class TableCell(MarkdownNode):
    children: tuple[InlineNode, ...] = ()
    colspan: int = 1
    rowspan: int = 1


@dataclass(frozen=True, slots=True)
class Table(BlockNode):
    header: tuple[TableCell, ...] = ()
    rows: tuple[tuple[TableCell, ...], ...] = ()
    alignments: tuple[Alignment, ...] = ()
    outer_pipes: bool = True
    caption: str = ""

    def __post_init__(self) -> None:
        if self.alignments and len(self.alignments) != len(self.header):
            raise ValueError("one alignment is required per header cell")


@dataclass(frozen=True, slots=True)
class FrontMatter(BlockNode):
    format: Literal["yaml", "toml", "json"]
    content: str


@dataclass(frozen=True, slots=True)
class MathBlock(BlockNode):
    expression: str
    delimiter: MathDelimiter = "dollar"
    environment: str = ""


@dataclass(frozen=True, slots=True)
class LinkDefinition(MarkdownNode):
    label: str
    destination: str
    title: str = ""
    title_delimiter: ReferenceTitleDelimiter = '"'


@dataclass(frozen=True, slots=True)
class FootnoteDefinition(MarkdownNode):
    label: str
    children: tuple[BlockNode, ...] = ()


# --------------------------------------------------------------------------
# Inline nodes
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Text(InlineNode):
    content: str


@dataclass(frozen=True, slots=True)
class Escape(InlineNode):
    character: str

    def __post_init__(self) -> None:
        if len(self.character) != 1:
            raise ValueError("Escape holds exactly one character")


@dataclass(frozen=True, slots=True)
class CharacterReference(InlineNode):
    value: str
    kind: ReferenceKind = "named"


@dataclass(frozen=True, slots=True)
class Emphasis(InlineNode):
    children: tuple[InlineNode, ...] = ()
    level: EmphasisLevel = 1
    delimiter: Literal["*", "_"] = "*"


@dataclass(frozen=True, slots=True)
class CodeSpan(InlineNode):
    code: str


@dataclass(frozen=True, slots=True)
class Link(InlineNode):
    children: tuple[InlineNode, ...] = ()
    destination: str = ""
    title: str = ""
    kind: InlineKind = "inline"
    label: str = ""
    title_delimiter: ReferenceTitleDelimiter = '"'


@dataclass(frozen=True, slots=True)
class Image(InlineNode):
    alt: tuple[InlineNode, ...] = ()
    destination: str = ""
    title: str = ""
    kind: InlineKind = "inline"
    label: str = ""
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class Autolink(InlineNode):
    target: str
    is_email: bool = False


@dataclass(frozen=True, slots=True)
class RawHTML(InlineNode):
    content: str


@dataclass(frozen=True, slots=True)
class LineBreak(InlineNode):
    hard: bool = True
    style: LineBreakStyle = "spaces"

    def __post_init__(self) -> None:
        if not self.hard and self.style != "soft":
            raise ValueError("soft line breaks must use the 'soft' style")
        if self.hard and self.style == "soft":
            raise ValueError("hard line breaks cannot use the 'soft' style")


@dataclass(frozen=True, slots=True)
class FootnoteReference(InlineNode):
    label: str


@dataclass(frozen=True, slots=True)
class Math(InlineNode):
    expression: str
    delimiter: MathDelimiter = "dollar"


# --------------------------------------------------------------------------
# Traversal
# --------------------------------------------------------------------------


def children_of(node: MarkdownNode) -> tuple[MarkdownNode, ...]:
    """Return the direct children of ``node`` in document order."""
    if isinstance(
        node, Document | Heading | Paragraph | ListItem | Blockquote | Callout
    ):
        return tuple(node.children)
    if isinstance(node, FootnoteDefinition):
        return tuple(node.children)
    if isinstance(node, ListBlock):
        return tuple(node.items)
    if isinstance(node, Table):
        cells = (*node.header, *(cell for row in node.rows for cell in row))
        return tuple(cells)
    if isinstance(node, TableCell):
        return tuple(node.children)
    if isinstance(node, Emphasis | Link):
        return tuple(node.children)
    if isinstance(node, Image):
        return tuple(node.alt)
    return ()


def walk(node: MarkdownNode) -> tuple[MarkdownNode, ...]:
    """Depth-first pre-order traversal as an immutable sequence."""
    collected: list[MarkdownNode] = []
    stack: list[MarkdownNode] = [node]
    while stack:
        current = stack.pop()
        collected.append(current)
        stack.extend(reversed(children_of(current)))
    return tuple(collected)


def text_content(inlines: tuple[InlineNode, ...]) -> str:
    """Concatenate the literal text carried by an inline sequence."""
    parts: list[str] = []
    for node in walk(Paragraph(children=inlines)):
        if isinstance(node, Text):
            parts.append(node.content)
    return "".join(parts)
