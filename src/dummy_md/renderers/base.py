"""Rendering primitives: mode-aware escaping and the renderer base class."""

from __future__ import annotations

import re
from typing import Literal

from dummy_md.core.dialects import Dialect
from dummy_md.core.nodes import (
    BlockNode,
    Document,
    FootnoteDefinition,
    InlineNode,
    LinkDefinition,
)
from dummy_md.exceptions import DialectError, RenderError

InlineMode = Literal["text", "heading", "table_cell", "link_label", "image_alt"]

# Characters that would otherwise begin inline markup.
_TEXT_ESCAPES: frozenset[str] = frozenset("\\`*_[]<>&~")
_LABEL_ESCAPES: frozenset[str] = frozenset("\\`[]")
_ESCAPES: dict[InlineMode, frozenset[str]] = {
    "text": _TEXT_ESCAPES,
    "heading": _TEXT_ESCAPES,
    "table_cell": _TEXT_ESCAPES | {"|"},
    "link_label": _LABEL_ESCAPES,
    "image_alt": _LABEL_ESCAPES,
}
_LINE_START = frozenset("#>+-=")
_ORDERED_START = re.compile(r"^(\d{1,9})([.)])")
_RUN_CACHE: dict[tuple[str, str], int] = {}


def escape_text(
    text: str, mode: InlineMode = "text", *, at_line_start: bool = False
) -> str:
    """Backslash-escape only the characters that matter in ``mode``."""
    escapes = _ESCAPES[mode]
    pieces: list[str] = []
    for character in text:
        if character in escapes:
            pieces.append("\\" + character)
        elif character == "\n":
            pieces.append(" ")
        else:
            pieces.append(character)
    escaped = "".join(pieces)
    if at_line_start and escaped:
        escaped = _escape_line_start(escaped)
    return escaped


def _escape_line_start(text: str) -> str:
    if text[0] in _LINE_START:
        return "\\" + text
    match = _ORDERED_START.match(text)
    if match:
        digits, delimiter = match.groups()
        return f"{digits}\\{delimiter}{text[len(digits) + 1 :]}"
    return text


def longest_run(text: str, character: str) -> int:
    """Length of the longest consecutive run of ``character`` in ``text``."""
    key = (text, character)
    cached = _RUN_CACHE.get(key)
    if cached is None:
        cached = 0
        current = 0
        for candidate in text:
            current = current + 1 if candidate == character else 0
            cached = max(cached, current)
        if len(_RUN_CACHE) > 4096:
            _RUN_CACHE.clear()
        _RUN_CACHE[key] = cached
    return cached


def fence_for(
    code: str, preferred: Literal["`", "~"] = "`", minimum: int = 3
) -> tuple[str, int]:
    """Pick a fence character and length that cannot appear inside ``code``."""
    character = preferred
    if character == "`" and "```" in code:
        return "~", max(minimum, longest_run(code, "~") + 1)
    return character, max(minimum, longest_run(code, character) + 1)


def format_destination(
    destination: str, *, title: str = "", title_delimiter: str = '"'
) -> str:
    """Render ``destination`` plus an optional title, escaping as required."""
    if destination == "":
        rendered = ""
    elif any(character in destination for character in " ()<>"):
        inner = (
            destination.replace("\\", "\\\\").replace("<", "\\<").replace(">", "\\>")
        )
        rendered = f"<{inner}>"
    else:
        escaped = destination.replace("\\", "\\\\")
        for character in "()":
            escaped = escaped.replace(character, "\\" + character)
        rendered = escaped
    if not title:
        return rendered
    if title_delimiter == "(":
        inner_title = title.replace("(", "\\(").replace(")", "\\)")
        suffix = f" ({inner_title})"
    else:
        inner_title = title.replace(title_delimiter, "\\" + title_delimiter)
        suffix = f" {title_delimiter}{inner_title}{title_delimiter}"
    return rendered + suffix


class BaseRenderer:
    """Shared document assembly; concrete dialects supply the node formatting."""

    dialect: Dialect

    def __init__(self, dialect: Dialect) -> None:
        self.dialect = dialect

    # -- public -----------------------------------------------------------
    def render(self, document: Document) -> str:
        parts: list[str] = []
        body = self.render_blocks(document.children)
        if body:
            parts.append(body)
        definitions = self.render_definitions(document)
        if definitions:
            parts.append(definitions)
        if not parts:
            return ""
        return "\n\n".join(parts) + "\n"

    def render_blocks(self, blocks: tuple[BlockNode, ...]) -> str:
        rendered = [self.render_block(block) for block in blocks]
        return "\n\n".join(part for part in rendered if part)

    def render_definitions(self, document: Document) -> str:
        parts: list[str] = []
        for definition in document.link_definitions:
            parts.append(self.render_link_definition(definition))
        for footnote in document.footnote_definitions:
            parts.append(self.render_footnote_definition(footnote))
        return "\n".join(parts)

    def render_link_definition(self, definition: LinkDefinition) -> str:
        if not self.dialect.supports("link.definition"):
            raise DialectError(
                f"link definitions are not available in {self.dialect.name!r}",
                dialects=("commonmark", "gfm", "extended", "stress"),
            )
        label = escape_text(definition.label, "link_label")
        target = format_destination(
            definition.destination,
            title=definition.title,
            title_delimiter=definition.title_delimiter,
        )
        return f"[{label}]: {target}"

    def render_footnote_definition(self, footnote: FootnoteDefinition) -> str:
        if not self.dialect.supports("footnote.definition"):
            raise DialectError(
                f"footnotes are not available in {self.dialect.name!r}",
                dialects=("extended", "stress"),
            )
        if not footnote.children:
            return f"[^{footnote.label}]:"
        blocks = [self.render_block(child) for child in footnote.children]
        rendered = "\n\n".join(block for block in blocks if block)
        lines = rendered.split("\n")
        head, *tail = lines
        indented = "\n".join("    " + line if line else "" for line in tail)
        definition = f"[^{footnote.label}]: {head}"
        return definition + ("\n" + indented if indented else "")

    # -- overridden by dialects ------------------------------------------
    def render_block(self, node: BlockNode) -> str:
        raise RenderError(f"{type(self).__name__} cannot render {type(node).__name__}")

    def render_inline(
        self,
        node: InlineNode,
        mode: InlineMode = "text",
        *,
        at_line_start: bool = False,
    ) -> str:
        raise RenderError(f"{type(self).__name__} cannot render {type(node).__name__}")

    # -- capability guard -------------------------------------------------
    def require(self, feature_id: str, description: str) -> None:
        if self.dialect.supports(feature_id):
            return
        raise DialectError(
            f"{description} are not available in dialect {self.dialect.name!r}",
            dialects=_dialects_supporting(feature_id),
        )

    def require_any(self, feature_ids: tuple[str, ...], description: str) -> None:
        """Accept any one of several equivalent feature ids."""
        if any(self.dialect.supports(feature_id) for feature_id in feature_ids):
            return
        order = ("commonmark", "gfm", "extended", "stress")
        supported: set[str] = set()
        for feature_id in feature_ids:
            supported.update(_dialects_supporting(feature_id))
        raise DialectError(
            f"{description} are not available in dialect {self.dialect.name!r}",
            dialects=tuple(name for name in order if name in supported),
        )


def _dialects_supporting(feature_id: str) -> tuple[str, ...]:
    from dummy_md.core.catalog import CATALOG_BY_ID

    spec = CATALOG_BY_ID.get(feature_id)
    if spec is None:
        return ()
    order = ("commonmark", "gfm", "extended", "stress")
    return tuple(name for name in order if name in spec.dialects)
