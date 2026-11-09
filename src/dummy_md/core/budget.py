"""Length units, measurement, and the budget ledger."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

from dummy_md.core.nodes import (
    BlockNode,
    Document,
    Heading,
    LineBreak,
    Paragraph,
    Text,
    walk,
)
from dummy_md.exceptions import BudgetError

if TYPE_CHECKING:
    from dummy_md.core.context import GenerationContext
    from dummy_md.renderers.base import BaseRenderer

Unit = Literal["chars", "words", "lines", "blocks", "bytes"]
Mode = Literal["approximate", "exact"]

UNITS: tuple[str, ...] = ("chars", "words", "lines", "blocks", "bytes")


def measure_text(text: str, unit: Unit) -> int:
    """Measure already-serialized output.

    ``chars`` excludes the trailing newline every renderer emits, so the count
    matches what a user sees in an editor's character counter.
    """
    if unit == "chars":
        return len(text[:-1]) if text.endswith("\n") else len(text)
    if unit == "lines":
        if not text:
            return 0
        return text.count("\n") + (0 if text.endswith("\n") else 1)
    if unit == "bytes":
        return len(text.encode("utf-8"))
    raise ValueError(f"unit {unit!r} is not a serialized unit")


def count_words(document: Document) -> int:
    words = 0
    for node in walk(document):
        if isinstance(node, Text):
            words += len(node.content.split())
    return words


def count_blocks(document: Document) -> int:
    return len(document.children)


def measure(document: Document, text: str, unit: Unit) -> int:
    if unit == "words":
        return count_words(document)
    if unit == "blocks":
        return count_blocks(document)
    return measure_text(text, unit)


@dataclass(slots=True)
class BudgetTracker:
    """Running ledger for the active unit."""

    unit: Unit
    target: int
    mode: Mode = "approximate"
    tolerance: float = 0.05
    consumed: int = 0

    def __post_init__(self) -> None:
        if self.target < 0:
            raise ValueError("budget target must be non-negative")
        if self.unit not in UNITS:
            raise ValueError(f"unknown unit {self.unit!r}")
        if self.mode not in {"approximate", "exact"}:
            raise ValueError(f"unknown mode {self.mode!r}")
        if not 0 <= self.tolerance <= 1:
            raise ValueError("tolerance must be between 0 and 1")

    @property
    def remaining(self) -> int:
        return self.target - self.consumed

    def record(self, amount: int) -> None:
        self.consumed += amount

    def delta(self, actual: int) -> int:
        return self.target - actual

    def accepts(self, actual: int) -> bool:
        if self.mode == "exact":
            return actual == self.target
        if self.target == 0:
            return actual == 0
        return abs(actual - self.target) <= self.tolerance * self.target

    def enforce(self, actual: int, *, operation: str = "document") -> None:
        if self.accepts(actual):
            return
        raise BudgetError(
            f"{self.unit} target not reached by {operation}",
            requested=self.target,
            achievable=actual,
        )


# --------------------------------------------------------------------------
# Elastic fitting
# --------------------------------------------------------------------------

MAX_FIT_STEPS = 512


def fit(
    document: Document,
    renderer: BaseRenderer,
    tracker: BudgetTracker,
    context: GenerationContext,
    *,
    floor_blocks: int = 1,
) -> str:
    """Resize elastic paragraphs until the rendered document meets the budget."""
    return fit_document(
        document, renderer, tracker, context, floor_blocks=floor_blocks
    )[1]


def fit_document(
    document: Document,
    renderer: BaseRenderer,
    tracker: BudgetTracker,
    context: GenerationContext,
    *,
    floor_blocks: int = 1,
) -> tuple[Document, str]:
    """Fit the document and return both the adjusted AST and its rendering."""
    text = renderer.render(document)
    for _ in range(MAX_FIT_STEPS):
        actual = measure(document, text, tracker.unit)
        if tracker.accepts(actual):
            return document, text
        if actual < tracker.target:
            adjusted = _grow(document, context, tracker.target - actual, tracker.unit)
        else:
            adjusted = _shrink(
                document,
                context,
                actual - tracker.target,
                tracker.unit,
                floor_blocks,
            )
        if adjusted is document:
            break
        adjusted_text = renderer.render(adjusted)
        if adjusted_text == text:
            break
        document, text = adjusted, adjusted_text
    tracker.enforce(measure(document, text, tracker.unit))
    return document, text


def _grow(
    document: Document, context: GenerationContext, delta: int, unit: Unit
) -> Document:
    if unit in {"chars", "bytes"}:
        return _grow_chars(document, context, delta)
    if unit == "words":
        return _grow_words(document, context)
    if unit == "lines":
        return _grow_lines(document, context)
    return _append_block(document, context)


def _shrink(
    document: Document,
    context: GenerationContext,
    delta: int,
    unit: Unit,
    floor_blocks: int,
) -> Document:
    if unit in {"chars", "bytes"}:
        return _shrink_chars(document, floor_blocks)
    if unit == "words":
        return _shrink_words(document, floor_blocks)
    if unit == "lines":
        return _shrink_lines(document, floor_blocks)
    return _drop_block(document, floor_blocks)


def _replace_last(document: Document, block: BlockNode) -> Document:
    blocks = list(document.children)
    if not blocks:
        return replace(document, children=(block,))
    blocks[-1] = block
    return replace(document, children=tuple(blocks))


def _append_block(document: Document, context: GenerationContext) -> Document:
    block = Paragraph(children=(Text(context.text.sentence()),))
    return replace(document, children=(*document.children, block))


def _drop_block(document: Document, floor_blocks: int) -> Document:
    if len(document.children) <= floor_blocks:
        return document
    return replace(document, children=document.children[:-1])


_ELASTIC_TYPES = (Paragraph, Heading)


def _append_suffix(block: BlockNode, suffix: str) -> BlockNode:
    if not isinstance(block, _ELASTIC_TYPES):
        raise TypeError(f"{type(block).__name__} is not elastic")
    children = list(block.children)
    if children and isinstance(children[-1], Text):
        children[-1] = Text(children[-1].content + suffix)
    else:
        children.append(Text(suffix.lstrip() or suffix))
    return replace(block, children=tuple(children))


def _grow_chars(document: Document, context: GenerationContext, delta: int) -> Document:
    if not document.children or not isinstance(document.children[-1], _ELASTIC_TYPES):
        return _append_block(document, context)
    paragraph = document.children[-1]
    if delta > 40:
        suffix = " " + context.text.sentence()
    elif delta >= 2:
        suffix = " " + context.text.word_of_length(delta - 1)
    else:
        last = paragraph.children[-1] if paragraph.children else None
        ending = last.content[-1:] if isinstance(last, Text) else ""
        suffix = "!" if ending in {".", "!", "?"} else "."
    return _replace_last(document, _append_suffix(paragraph, suffix))


def _shrink_chars(document: Document, floor_blocks: int) -> Document:
    blocks = list(document.children)
    if not blocks:
        return document
    last = blocks[-1]
    if not isinstance(last, _ELASTIC_TYPES) or not last.children:
        return _drop_block(document, floor_blocks)
    children = list(last.children)
    for index in range(len(children) - 1, -1, -1):
        child = children[index]
        if not isinstance(child, Text):
            continue
        content = child.content.rstrip()
        head, _, _tail = content.rpartition(" ")
        if head:
            children[index] = Text(head)
        elif len(content) > 1:
            children[index] = Text(content[:-1])
        else:
            children.pop(index)
        break
    else:
        return _drop_block(document, floor_blocks)
    if children:
        blocks[-1] = replace(last, children=tuple(children))
    elif len(blocks) > floor_blocks:
        blocks.pop()
    else:
        return document
    return replace(document, children=tuple(blocks))


def _grow_words(document: Document, context: GenerationContext) -> Document:
    if not document.children or not isinstance(document.children[-1], _ELASTIC_TYPES):
        return _append_block(document, context)
    paragraph = document.children[-1]
    return _replace_last(document, _append_suffix(paragraph, " " + context.text.word()))


def _shrink_words(document: Document, floor_blocks: int) -> Document:
    blocks = list(document.children)
    if not blocks:
        return document
    last = blocks[-1]
    if not isinstance(last, _ELASTIC_TYPES) or not last.children:
        return _drop_block(document, floor_blocks)
    children = list(last.children)
    for index in range(len(children) - 1, -1, -1):
        child = children[index]
        if not isinstance(child, Text):
            continue
        content = child.content.rstrip()
        head, _, _tail = content.rpartition(" ")
        if head:
            children[index] = Text(head)
        else:
            children.pop(index)
        break
    else:
        return _drop_block(document, floor_blocks)
    if children:
        blocks[-1] = replace(last, children=tuple(children))
    elif len(blocks) > floor_blocks:
        blocks.pop()
    else:
        return document
    return replace(document, children=tuple(blocks))


def _grow_lines(document: Document, context: GenerationContext) -> Document:
    if not document.children or not isinstance(document.children[-1], Paragraph):
        return _append_block(document, context)
    paragraph = document.children[-1]
    children = (
        *paragraph.children,
        LineBreak(hard=False, style="soft"),
        Text(context.text.sentence()),
    )
    return _replace_last(document, Paragraph(children=children))


def _shrink_lines(document: Document, floor_blocks: int) -> Document:
    blocks = list(document.children)
    if not blocks:
        return document
    last = blocks[-1]
    if not isinstance(last, Paragraph):
        return _drop_block(document, floor_blocks)
    cut = None
    for index in range(len(last.children) - 1, -1, -1):
        if isinstance(last.children[index], LineBreak):
            cut = index
            break
    if cut is None:
        return _drop_block(document, floor_blocks)
    if cut == 0:
        if len(blocks) <= floor_blocks:
            return document
        blocks.pop()
    else:
        blocks[-1] = Paragraph(children=last.children[:cut])
    return replace(document, children=tuple(blocks))
