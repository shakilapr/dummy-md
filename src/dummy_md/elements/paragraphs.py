"""Paragraph generation with inline formatting injection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    BlockNode,
    CodeSpan,
    Emphasis,
    InlineNode,
    LineBreak,
    Paragraph,
    Strikethrough,
    Text,
)
from dummy_md.elements._util import resolve_options

_EMPHASIS: dict[str, Callable[[str], InlineNode]] = {
    "inline.emphasis.asterisk": lambda text: Emphasis(
        children=(Text(text),), level=1, delimiter="*"
    ),
    "inline.emphasis.underscore": lambda text: Emphasis(
        children=(Text(text),), level=1, delimiter="_"
    ),
    "inline.strong.asterisk": lambda text: Emphasis(
        children=(Text(text),), level=2, delimiter="*"
    ),
    "inline.strong.underscore": lambda text: Emphasis(
        children=(Text(text),), level=2, delimiter="_"
    ),
    "inline.strong_emphasis.triple": lambda text: Emphasis(
        children=(Text(text),), level=3, delimiter="*"
    ),
    "inline.emphasis.nested": lambda text: Emphasis(
        children=(Emphasis(children=(Text(text),), level=1, delimiter="_"),),
        level=2,
        delimiter="*",
    ),
    "inline.strikethrough": lambda text: Strikethrough(children=(Text(text),)),
    "inline.code_span": lambda text: CodeSpan(code=text),
    "inline.code_span.multi_backtick": lambda text: CodeSpan(code="`" + text + "`"),
    "inline.code_span.backtick_content": lambda text: CodeSpan(code=text + "`"),
}


@dataclass(frozen=True, slots=True)
class ParagraphOptions:
    min_sentences: int = 2
    max_sentences: int = 5
    inline_ratio: float = 0.75
    max_inline: int = 3
    break_ratio: float = 0.35


class ParagraphGenerator:
    """Produces paragraphs, optionally multi-line and inline-decorated."""

    family = "paragraph"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, ParagraphOptions(), ParagraphOptions
        )
        count = context.rng.randint(options.min_sentences, options.max_sentences)
        builders = [
            _EMPHASIS[feature]
            for feature in context.active_in_family("inline")
            if feature in _EMPHASIS
        ]

        children: list[InlineNode] = []
        decorations = 0
        for index in range(count):
            if index:
                break_node = self._inter_sentence_break(context, options)
                children.append(break_node if break_node else Text(" "))
            use_decoration = (
                builders
                and decorations < options.max_inline
                and context.rng.random() < options.inline_ratio
            )
            if use_decoration:
                builder = context.rng.choice(builders)
                children.extend(self._decorate(context, builder))
                decorations += 1
            else:
                children.append(Text(context.text.sentence()))

        if context.supports("inline.emoji.unicode") and context.rng.random() < 0.25:
            children.append(Text(" \U0001f642"))
        return Paragraph(children=tuple(children))

    # -- helpers ----------------------------------------------------------
    def _inter_sentence_break(
        self, context: GenerationContext, options: ParagraphOptions
    ) -> LineBreak | None:
        if not context.supports("paragraph.multi_line"):
            return None
        if context.rng.random() >= options.break_ratio:
            return None
        styles: list[LineBreak] = []
        if context.supports("paragraph.linebreak.hard_spaces"):
            styles.append(LineBreak(hard=True, style="spaces"))
        if context.supports("paragraph.linebreak.hard_backslash"):
            styles.append(LineBreak(hard=True, style="backslash"))
        if context.supports("paragraph.linebreak.soft"):
            styles.append(LineBreak(hard=False, style="soft"))
        if not styles:
            return LineBreak(hard=False, style="soft")
        return context.rng.choice(styles)

    def _decorate(
        self, context: GenerationContext, builder: Callable[[str], InlineNode]
    ) -> tuple[InlineNode, ...]:
        sentence = context.text.sentence(min_words=6, max_words=14)
        words = sentence.split(" ")
        if len(words) < 5:
            return (Text(sentence),)
        start = context.rng.randint(1, len(words) - 3)
        span = context.rng.randint(1, min(2, len(words) - start - 1))
        end = start + span
        before = " ".join(words[:start]) + " "
        inner = " ".join(words[start:end])
        after = " " + " ".join(words[end:])
        return (Text(before), builder(inner), Text(after))
