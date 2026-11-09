"""Strict CommonMark serialization.

Every node formatter lives here; GFM subclasses add the constructs CommonMark
does not define. Constructs from other dialects are implemented but guarded by
``require``, so a CommonMark renderer rejects them with :class:`DialectError`.
"""

from __future__ import annotations

from dummy_md.core.nodes import (
    AbbreviationDefinition,
    Attributes,
    Autolink,
    BlockNode,
    Blockquote,
    Callout,
    CharacterReference,
    CodeBlock,
    CodeSpan,
    Critic,
    CrossRef,
    DefinitionList,
    EmojiShortcode,
    Emphasis,
    Escape,
    FencedDiv,
    Figure,
    FootnoteReference,
    FrontMatter,
    Heading,
    HTMLBlock,
    Image,
    InlineFootnote,
    InlineNode,
    LineBlock,
    LineBreak,
    Link,
    ListBlock,
    ListItem,
    Math,
    MathBlock,
    MathMacros,
    Paragraph,
    RawHTML,
    Span,
    Strikethrough,
    StyledSpan,
    Table,
    Text,
    ThematicBreak,
    WikiLink,
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

_STYLED_SPANS: dict[str, tuple[str, str, str]] = {
    "superscript": ("inline.superscript", "^", "^"),
    "subscript": ("inline.subscript", "~", "~"),
    "underline": ("inline.underline", "++", "++"),
    "highlight": ("inline.highlight", "==", "=="),
    "insert": ("inline.insert", "^^", "^^"),
}


def _alpha_number(value: int) -> str:
    if value < 1:
        return "a"
    letters: list[str] = []
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        letters.append(chr(ord("a") + remainder))
    return "".join(reversed(letters))


def _roman_number(value: int) -> str:
    if value < 1:
        return "i"
    table = (
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    )
    out: list[str] = []
    remaining = value
    for amount, numeral in table:
        while remaining >= amount:
            out.append(numeral)
            remaining -= amount
    return "".join(out)


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
            return self._quote(node)
        if isinstance(node, Callout):
            return self._callout(node)
        if isinstance(node, Table):
            self.require("table.pipe", "pipe tables")
            return self._table(node)
        if isinstance(node, FrontMatter):
            return self._front_matter(node)
        if isinstance(node, MathBlock):
            return self._math_block(node)
        if isinstance(node, Figure):
            return self._figure(node)
        if isinstance(node, LineBlock):
            return self._line_block(node)
        if isinstance(node, FencedDiv):
            return self._fenced_div(node)
        if isinstance(node, DefinitionList):
            return self._definition_list(node)
        if isinstance(node, AbbreviationDefinition):
            self.require("inline.abbreviation.definition", "abbreviation definitions")
            return f"*[{node.label}]: {node.title}"
        if isinstance(node, MathMacros):
            return self._math_macros(node)
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
            return f"<{node.target}>" if node.bracketed else node.target
        if isinstance(node, RawHTML):
            return node.content
        if isinstance(node, FootnoteReference):
            self.require("footnote.reference", "footnotes")
            return f"[^{node.label}]"
        if isinstance(node, Math):
            return self._math(node)
        if isinstance(node, InlineFootnote):
            self.require("footnote.inline", "inline footnotes")
            return "^[" + self._inline_sequence(node.children, mode) + "]"
        if isinstance(node, StyledSpan):
            return self._styled_span(node, mode)
        if isinstance(node, Critic):
            return self._critic(node, mode)
        if isinstance(node, EmojiShortcode):
            self.require("inline.emoji.shortcode", "emoji shortcodes")
            return f":{node.name}:"
        if isinstance(node, WikiLink):
            return self._wiki_link(node)
        if isinstance(node, Span):
            return self._span(node, mode)
        if isinstance(node, CrossRef):
            self.require("math.crossref", "cross-references")
            return "[@" + node.target + "]"
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
            return f"{text}{attributes}\n{underline * max(3, len(text))}"
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
        info = node.info + self._attributes(node.attributes, "code")
        opening = fence + info
        block = f"{opening}\n{code}\n{fence}"
        if node.caption:
            self.require("code.caption", "code captions")
            block += f"\n\n: {escape_text(node.caption)}"
        return block

    def _list(self, node: ListBlock) -> str:
        if any(item.checked is not None for item in node.items):
            self.require_any(
                (
                    "list.task.unchecked",
                    "list.task.checked",
                    "list.task.mixed",
                ),
                "task lists",
            )
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
        number = node.start + index
        if node.style == "example":
            self.require("list.example_numbered", "example lists")
            return "(@) "
        if node.style == "alpha":
            self.require("list.ordered.alpha", "alphabetical lists")
            return f"{_alpha_number(number)}{node.delimiter} "
        if node.style == "roman":
            self.require("list.ordered.roman", "Roman-numeral lists")
            return f"{_roman_number(number)}{node.delimiter} "
        if node.ordered:
            return f"{number}{node.delimiter} "
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

    def _quote(self, node: Blockquote) -> str:
        body = self.render_blocks(node.children)
        lines = body.split("\n")
        rendered: list[str] = []
        in_paragraph = False
        for index, line in enumerate(lines):
            if not line:
                rendered.append(">")
                in_paragraph = False
                continue
            if index == 0:
                rendered.append("> " + line)
                in_paragraph = True
                continue
            if node.lazy and in_paragraph:
                # Lazy continuation: wrapped paragraph lines may omit the marker.
                self.require("blockquote.lazy", "lazy blockquote continuation")
                rendered.append(line)
            else:
                rendered.append("> " + line)
        return "\n".join(rendered)

    def _callout(self, node: Callout) -> str:
        self.require_any(
            (
                f"callout.github.{node.kind}",
                f"callout.obsidian.{node.kind}",
            ),
            "callouts",
        )
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
            return node.content.strip("\n")
        fence = "---" if node.format == "yaml" else "+++"
        return f"{fence}\n{node.content.strip(chr(10))}\n{fence}"

    def _math_block(self, node: MathBlock) -> str:
        expression = node.expression.strip("\n")
        labelled = (
            expression + "\n\\label{" + node.label + "}" if node.label else expression
        )
        if node.environment:
            self.require(f"math.latex.{node.environment}", "LaTeX environments")
            begin = f"\\begin{{{node.environment}}}"
            end = f"\\end{{{node.environment}}}"
            return f"{begin}\n{labelled}\n{end}"
        feature = (
            "math.display.bracket"
            if node.delimiter == "bracket"
            else "math.display.dollar"
        )
        self.require(feature, "display math")
        if node.delimiter == "bracket":
            return f"\\[\n{labelled}\n\\]"
        return f"$$\n{labelled}\n$$"

    def _figure(self, node: Figure) -> str:
        if node.caption:
            self.require("image.figure.caption", "figure captions")
        if node.label:
            self.require("image.figure.label", "figure labels")
        alt = self._inline_sequence(
            (Text(node.caption),) if node.caption else node.image.alt, "image_alt"
        )
        target = format_destination(
            node.image.destination,
            title=node.image.title,
            title_delimiter=node.image.title_delimiter,
        )
        attributes: list[str] = []
        if node.image.width is not None:
            self.require("image.width", "image width attributes")
            attributes.append(f"width={node.image.width}")
        if node.image.height is not None:
            self.require("image.height", "image height attributes")
            attributes.append(f"height={node.image.height}")
        if node.label:
            attributes.append("#" + node.label)
        rendered = f"![{alt}]({target})"
        if attributes:
            rendered += "{" + " ".join(attributes) + "}"
        return rendered

    def _line_block(self, node: LineBlock) -> str:
        self.require("paragraph.line_block", "line blocks")
        lines = [
            "| " + self._inline_sequence(line, "text") if line else "|"
            for line in node.lines
        ]
        return "\n".join(lines)

    def _fenced_div(self, node: FencedDiv) -> str:
        self.require("paragraph.fenced_div", "fenced divs")
        attributes = node.attributes
        if node.info:
            classes = tuple(attributes.classes) if attributes else ()
            attributes = Attributes(
                identifier=attributes.identifier if attributes else None,
                classes=(node.info, *(name for name in classes if name != node.info)),
                pairs=attributes.pairs if attributes else (),
            )
        header = ":::" + (
            " " + self._attribute_string(attributes) if attributes else ""
        )
        body = self.render_blocks(node.children)
        return f"{header}\n{body}\n:::" if body else f"{header}\n:::"

    def _definition_list(self, node: DefinitionList) -> str:
        self.require("list.definition", "definition lists")
        blocks: list[str] = []
        for item in node.items:
            blocks.append(self._inline_sequence(item.term, "text"))
            for definition in item.definitions:
                body = self.render_blocks(definition)
                blocks.append(": " + body.replace("\n", "\n  "))
        return "\n\n".join(blocks)

    def _math_macros(self, node: MathMacros) -> str:
        self.require("math.macros", "LaTeX macros")
        return "\n".join(
            f"\\newcommand{{\\{name}}}{{{body}}}" for name, body in node.definitions
        )

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
            rendered = f"[{text}]({target})"
            if node.attributes and not node.attributes.is_empty():
                self.require("link.attributes", "link attributes")
                rendered += self._attribute_string(node.attributes)
            return rendered
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
        feature = (
            "math.inline.paren" if node.delimiter == "bracket" else "math.inline.dollar"
        )
        self.require(feature, "inline math")
        if node.delimiter == "bracket":
            return f"\\({node.expression}\\)"
        return f"${node.expression}$"

    # -- extended inlines --------------------------------------------------
    def _styled_span(self, node: StyledSpan, mode: InlineMode) -> str:
        feature, opening, closing = _STYLED_SPANS[node.syntax]
        self.require(feature, "inline styling")
        inner = self._inline_sequence(node.children, mode)
        return f"{opening}{inner}{closing}"

    def _critic(self, node: Critic, mode: InlineMode) -> str:
        self.require(f"inline.critic.{node.kind}", "CriticMarkup")
        inner = self._inline_sequence(node.children, mode)
        if node.kind == "replacement":
            replacement = self._inline_sequence(node.replacement, mode)
            return "{" + f"~~{inner}~>{replacement}~~" + "}"
        if node.kind == "deletion":
            return "{" + f"--{inner}--" + "}"
        if node.kind == "insertion":
            return "{" + f"++{inner}++" + "}"
        if node.kind == "comment":
            return "{" + f">>{inner}<<" + "}"
        return "{" + f"=={inner}==" + "}"

    def _wiki_link(self, node: WikiLink) -> str:
        self.require("link.wiki.basic", "wiki links")
        if node.alias:
            self.require("link.wiki.alias", "wiki link aliases")
        if node.heading:
            self.require("link.wiki.heading", "wiki links to headings")
        if node.block:
            self.require("link.wiki.block", "wiki links to block ids")
        target = node.target
        if node.heading:
            target += "#" + node.heading
        if node.block:
            target += "#^" + node.block
        if node.alias:
            return "[[" + target + "|" + node.alias + "]]"
        return "[[" + target + "]]"

    def _span(self, node: Span, mode: InlineMode) -> str:
        classes = node.attributes.classes if node.attributes else ()
        if "smallcaps" in classes:
            self.require("inline.small_caps", "small caps")
        inner = self._inline_sequence(node.children, mode)
        return "[" + inner + "]" + self._attribute_string(node.attributes)

    def _attribute_string(self, attributes: Attributes | None) -> str:
        if attributes is None or attributes.is_empty():
            return "{}"
        parts: list[str] = []
        if attributes.identifier:
            parts.append("#" + attributes.identifier)
        parts.extend("." + name for name in attributes.classes)
        parts.extend(
            key + '="' + escape_text(value, "text") + '"'
            for key, value in attributes.pairs
        )
        return "{" + " ".join(parts) + "}"

    # -- attributes -------------------------------------------------------
    def _attributes(self, attributes: Attributes | None, scope: str = "heading") -> str:
        if attributes is None or attributes.is_empty():
            return ""
        parts: list[str] = []
        if attributes.identifier:
            self.require(f"{scope}.attributes.identifier", f"{scope} attributes")
            parts.append("#" + attributes.identifier)
        for name in attributes.classes:
            self.require(f"{scope}.attributes.classes", f"{scope} attributes")
            parts.append("." + name)
        for key, value in attributes.pairs:
            parts.append(f'{key}="{escape_text(value, "text")}"')
        return " {" + " ".join(parts) + "}" if parts else ""


__all__ = ["CommonMarkRenderer"]
