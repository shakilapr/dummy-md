"""Strict CommonMark serialization.

Every node formatter lives here; GFM subclasses add the constructs CommonMark
does not define. Constructs from other dialects are implemented but guarded by
``require``, so a CommonMark renderer rejects them with :class:`DialectError`.
"""

from __future__ import annotations

from dummy_md.core.nodes import (
    Attributes,
    Autolink,
    BlockNode,
    Blockquote,
    Callout,
    CharacterReference,
    CodeBlock,
    CodeSpan,
    Emphasis,
    Escape,
    FootnoteReference,
    FrontMatter,
    Heading,
    HTMLBlock,
    Image,
    InlineNode,
    LineBreak,
    Link,
    ListBlock,
    ListItem,
    Math,
    MathBlock,
    Paragraph,
    RawHTML,
    Strikethrough,
    Table,
    Text,
    ThematicBreak,
)
from dummy_md.exceptions import DialectError, RenderError
from dummy_md.renderers.base import (
    BaseRenderer,
    InlineMode,
    escape_text,
    fence_for,
    format_destination,
    longest_run,
)


class CommonMarkRenderer(BaseRenderer):
    """Serialize the CommonMark subset plus guarded dialect extensions."""

    # -- blocks -----------------------------------------------------------
    def render_block(self, node: BlockNode) -> str:
        if isinstance(node, Heading):
            return self._heading(node)
        if isinstance(node, Paragraph):
            return self._paragraph(node)
        if isinstance(node, ThematicBreak):
            return self._thematic_break(node)
        if isinstance(node, CodeBlock):
            return self._code_block(node)
        if isinstance(node, HTMLBlock):
            return node.content
        if isinstance(node, ListBlock):
            return self._list(node)
        if isinstance(node, ListItem):
            return self.render_blocks(node.children)
        if isinstance(node, Blockquote):
            return self._quote(node.children)
        if isinstance(node, Callout):
            return self._callout(node)
        if isinstance(node, Table):
            self.require("table.pipe", "pipe tables")
            return self._table(node)
        if isinstance(node, FrontMatter):
            return self._front_matter(node)
        if isinstance(node, MathBlock):
            return self._math_block(node)
        raise RenderError(f"cannot render block {type(node).__name__}")

    # -- inlines ----------------------------------------------------------
    def render_inline(
        self,
        node: InlineNode,
        mode: InlineMode = "text",
        *,
        at_line_start: bool = False,
    ) -> str:
        if isinstance(node, Text):
            return escape_text(node.content, mode, at_line_start=at_line_start)
        if isinstance(node, Escape):
            return "\\" + node.character
        if isinstance(node, CharacterReference):
            return f"&{node.value};"
        if isinstance(node, Emphasis):
            delimiter = node.delimiter * node.level
            inner = self._inline_sequence(node.children, mode)
            return f"{delimiter}{inner}{delimiter}"
        if isinstance(node, Strikethrough):
            self.require("inline.strikethrough", "strikethrough")
            inner = self._inline_sequence(node.children, mode)
            return f"~~{inner}~~"
        if isinstance(node, CodeSpan):
            return self._code_span(node)
        if isinstance(node, Link):
            return self._link(node, mode)
        if isinstance(node, Image):
            return self._image(node, mode)
        if isinstance(node, Autolink):
            return f"<{node.target}>"
        if isinstance(node, RawHTML):
            return node.content
        if isinstance(node, FootnoteReference):
            self.require("footnote.reference", "footnotes")
            return f"[^{node.label}]"
        if isinstance(node, Math):
            return self._math(node)
        if isinstance(node, LineBreak):
            raise RenderError("line breaks are rendered by paragraphs")
        raise RenderError(f"cannot render inline {type(node).__name__}")

    # -- helpers ----------------------------------------------------------
    def _inline_sequence(self, nodes: tuple[InlineNode, ...], mode: InlineMode) -> str:
        return "".join(self.render_inline(node, mode) for node in nodes)

    def _heading(self, node: Heading) -> str:
        text = self._inline_sequence(node.children, "heading")
        attributes = self._attributes(node.attributes)
        if node.style == "setext":
            underline = "=" if node.level == 1 else "-"
            return f"{text}\n{underline * max(3, len(text))}{attributes}"
        marks = "#" * node.level
        closing = f" {marks}" if node.closed else ""
        return f"{marks} {text}{closing}{attributes}"

    def _paragraph(self, node: Paragraph) -> str:
        pieces: list[str] = []
        pending: LineBreak | None = None
        line_start = True
        for child in node.children:
            if isinstance(child, LineBreak):
                pending = child
                line_start = True
                continue
            if pending is not None:
                pieces.append(self._line_break(pending))
                pending = None
            pieces.append(self.render_inline(child, "text", at_line_start=line_start))
            line_start = False
        return "".join(pieces)

    def _line_break(self, node: LineBreak) -> str:
        if not node.hard:
            return "\n"
        if node.style == "backslash":
            return "\\\n"
        return "  \n"

    def _thematic_break(self, node: ThematicBreak) -> str:
        separator = " " * max(1, node.spacing) if node.spacing else ""
        return separator.join(node.character for _ in range(3))

    def _code_block(self, node: CodeBlock) -> str:
        code = node.code[:-1] if node.code.endswith("\n") else node.code
        if node.indented:
            return "\n".join("    " + line if line else "" for line in code.split("\n"))
        character, length = fence_for(code, node.fence_char, node.fence_length or 3)
        fence = character * length
        info = node.info + self._attributes(node.attributes)
        opening = fence + info
        block = f"{opening}\n{code}\n{fence}"
        if node.caption:
            self.require("code.caption", "code captions")
            block += f"\n\n: {escape_text(node.caption)}"
        return block

    def _list(self, node: ListBlock) -> str:
        if any(item.checked is not None for item in node.items):
            self.require("list.task.unchecked", "task lists")
        rendered_items = []
        for index, item in enumerate(node.items):
            marker = self._marker(node, index)
            body = self._list_item(item, tight=node.tight)
            lines = body.split("\n")
            prefixed = [
                marker + lines[0] if lines else marker.rstrip(),
                *[" " * len(marker) + line if line else "" for line in lines[1:]],
            ]
            rendered_items.append("\n".join(prefixed))
        separator = "\n" if node.tight else "\n\n"
        return separator.join(rendered_items)

    def _marker(self, node: ListBlock, index: int) -> str:
        if node.ordered:
            return f"{node.start + index}{node.delimiter} "
        return f"{node.delimiter} "

    def _list_item(self, item: ListItem, *, tight: bool) -> str:
        if tight and len(item.children) > 1:
            rendered: list[str] = []
            for position, child in enumerate(item.children):
                if position and not (
                    isinstance(child, Paragraph)
                    and isinstance(item.children[position - 1], Paragraph)
                ):
                    rendered.append("\n")
                elif position:
                    rendered.append("\n\n")
                rendered.append(self.render_block(child))
            body = "".join(rendered)
        else:
            body = self.render_blocks(item.children)
        if item.checked is None:
            return body
        box = "[x] " if item.checked else "[ ] "
        return box + body

    def _quote(self, children: tuple[BlockNode, ...]) -> str:
        body = self.render_blocks(children)
        return "\n".join("> " + line if line else ">" for line in body.split("\n"))

    def _callout(self, node: Callout) -> str:
        self.require("callout.github.note", "callouts")
        header = f"> [!{node.kind.upper()}]"
        if node.title:
            self.require("callout.title.custom", "custom callout titles")
            header += f" {escape_text(node.title)}"
        if node.foldable:
            self.require("callout.foldable.expanded", "foldable callouts")
            header += "-" if node.collapsed else "+"
        body = self.render_blocks(node.children)
        if not body:
            return header
        return (
            header
            + "\n"
            + "\n".join("> " + line if line else ">" for line in body.split("\n"))
        )

    def _table(self, node: Table) -> str:
        raise DialectError(
            f"pipe tables are not available in dialect {self.dialect.name!r}",
            dialects=("gfm", "extended", "stress"),
        )

    def _front_matter(self, node: FrontMatter) -> str:
        self.require("frontmatter.yaml", "front matter")
        if node.format == "json":
            return "{\n" + node.content.strip("\n") + "\n}"
        fence = "---" if node.format == "yaml" else "+++"
        return f"{fence}\n{node.content.strip(chr(10))}\n{fence}"

    def _math_block(self, node: MathBlock) -> str:
        self.require("math.display.dollar", "display math")
        expression = node.expression.strip("\n")
        if node.environment:
            begin = f"\\begin{{{node.environment}}}"
            end = f"\\end{{{node.environment}}}"
            return f"{begin}\n{expression}\n{end}"
        if node.delimiter == "bracket":
            return f"\\[\n{expression}\n\\]"
        return f"$$\n{expression}\n$$"

    # -- inline helpers ---------------------------------------------------
    def _code_span(self, node: CodeSpan) -> str:
        code = node.code
        delimiter = "`" * (longest_run(code, "`") + 1)
        if not code:
            return f"{delimiter} {delimiter}"
        padded = code.startswith("`") or code.endswith("`")
        if padded or (code.startswith(" ") and code.endswith(" ")):
            code = f" {code} "
        return f"{delimiter}{code}{delimiter}"

    def _link(self, node: Link, mode: InlineMode) -> str:
        text = self._inline_sequence(node.children, "link_label")
        if node.kind == "inline":
            target = format_destination(
                node.destination,
                title=node.title,
                title_delimiter=node.title_delimiter,
            )
            return f"[{text}]({target})"
        label = escape_text(node.label, "link_label")
        if node.kind == "full":
            return f"[{text}][{label}]"
        if node.kind == "collapsed":
            return f"[{label}][]"
        return f"[{label}]"

    def _image(self, node: Image, mode: InlineMode) -> str:
        alt = self._inline_sequence(node.alt, "image_alt")
        if node.kind == "inline":
            target = format_destination(
                node.destination,
                title=node.title,
                title_delimiter=node.title_delimiter,
            )
            rendered = f"![{alt}]({target})"
            attributes: list[str] = []
            if node.width is not None:
                self.require("image.width", "image width attributes")
                attributes.append(f"width={node.width}")
            if node.height is not None:
                self.require("image.height", "image height attributes")
                attributes.append(f"height={node.height}")
            if attributes:
                rendered += "{" + " ".join(attributes) + "}"
            return rendered
        label = escape_text(node.label, "link_label")
        if node.kind == "full":
            return f"![{alt}][{label}]"
        if node.kind == "collapsed":
            return f"![{label}][]"
        return f"![{label}]"

    def _math(self, node: Math) -> str:
        self.require("math.inline.dollar", "inline math")
        if node.delimiter == "bracket":
            return f"\\({node.expression}\\)"
        return f"${node.expression}$"

    def _attributes(self, attributes: Attributes | None) -> str:
        if attributes is None or attributes.is_empty():
            return ""
        parts: list[str] = []
        if attributes.identifier:
            self.require("heading.attributes.identifier", "heading attributes")
            parts.append("#" + attributes.identifier)
        for name in attributes.classes:
            self.require("heading.attributes.classes", "heading attributes")
            parts.append("." + name)
        for key, value in attributes.pairs:
            parts.append(f'{key}="{escape_text(value, "text")}"')
        return " {" + " ".join(parts) + "}" if parts else ""


__all__ = ["CommonMarkRenderer"]
