"""Paragraph generation with inline formatting injection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    AbbreviationDefinition,
    Attributes,
    BlockNode,
    CodeSpan,
    Critic,
    CrossRef,
    EmojiShortcode,
    Emphasis,
    FencedDiv,
    InlineFootnote,
    InlineNode,
    LineBlock,
    LineBreak,
    Math,
    Paragraph,
    Span,
    Strikethrough,
    StyledSpan,
    Text,
)
from dummy_md.elements._util import resolve_options


def _crossref_target(text: str) -> str:
    words = [
        "".join(ch for ch in word.lower() if ch.isalnum())
        for word in text.split(" ")[:2]
    ]
    cleaned = "-".join(word for word in words if word)
    return "eq:" + (cleaned or "label")


_INLINE_BUILDERS: dict[str, Callable[[str], InlineNode]] = {
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
    "math.inline.dollar": lambda text: Math(expression=text, delimiter="dollar"),
    "math.inline.paren": lambda text: Math(expression=text, delimiter="bracket"),
    "footnote.inline": lambda text: InlineFootnote(children=(Text(text),)),
    "inline.superscript": lambda text: StyledSpan(
        children=(Text(text.split(" ")[0]),), syntax="superscript"
    ),
    "inline.subscript": lambda text: StyledSpan(
        children=(Text(text.split(" ")[0]),), syntax="subscript"
    ),
    "inline.underline": lambda text: StyledSpan(
        children=(Text(text),), syntax="underline"
    ),
    "inline.highlight": lambda text: StyledSpan(
        children=(Text(text),), syntax="highlight"
    ),
    "inline.insert": lambda text: StyledSpan(children=(Text(text),), syntax="insert"),
    "inline.critic.deletion": lambda text: Critic(
        children=(Text(text),), kind="deletion"
    ),
    "inline.critic.insertion": lambda text: Critic(
        children=(Text(text),), kind="insertion"
    ),
    "inline.critic.replacement": lambda text: Critic(
        children=(Text(text),),
        kind="replacement",
        replacement=(Text(text.upper()),),
    ),
    "inline.critic.highlight": lambda text: Critic(
        children=(Text(text),), kind="highlight"
    ),
    "inline.critic.comment": lambda text: Critic(
        children=(Text(text),), kind="comment"
    ),
    "inline.emoji.shortcode": lambda text: EmojiShortcode(name="smile"),
    "inline.small_caps": lambda text: Span(
        children=(Text(text),), attributes=Attributes(classes=("smallcaps",))
    ),
    "math.crossref": lambda text: CrossRef(target=_crossref_target(text)),
}


@dataclass(frozen=True, slots=True)
class ParagraphOptions:
    min_sentences: int = 2
    max_sentences: int = 5
    sentence_min_words: int = 5
    sentence_max_words: int = 14
    inline_ratio: float = 0.75
    max_inline: int = 3
    break_ratio: float = 0.35
    emoji_ratio: float = 0.25
    block_ratio: float = 0.35


class ParagraphGenerator:
    """Produces paragraphs, optionally multi-line and inline-decorated."""

    family = "paragraph"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, ParagraphOptions(), ParagraphOptions
        )
        variant = self._block_variant(context, options)
        if variant is not None:
            return variant
        count = context.rng.randint(options.min_sentences, options.max_sentences)
        feature_ids = sorted(
            feature
            for feature in context.active_features
            if feature in _INLINE_BUILDERS
        )

        children: list[InlineNode] = []
        decorations = 0
        for index in range(count):
            if index:
                break_node = self._inter_sentence_break(context, options)
                children.append(break_node if break_node else Text(" "))
            use_decoration = (
                feature_ids
                and decorations < options.max_inline
                and context.rng.random() < options.inline_ratio
            )
            if use_decoration:
                builder = _INLINE_BUILDERS[context.weighted_feature(feature_ids)]
                children.extend(self._decorate(context, builder, options))
                decorations += 1
            else:
                children.append(Text(self._sentence(context, options)))

        if context.supports("inline.emoji.unicode") and (
            context.rng.random() < options.emoji_ratio
        ):
            children.append(Text(" \U0001f642"))
        if context.supports("inline.abbreviation.reference"):
            label = context.text.word(min_length=3, max_length=5).upper()
            children.insert(0, Text(label + " "))
        return Paragraph(children=tuple(children))

    # -- helpers ----------------------------------------------------------
    def _block_variant(
        self, context: GenerationContext, options: ParagraphOptions
    ) -> BlockNode | None:
        candidates: list[str] = []
        if context.supports("paragraph.line_block"):
            candidates.append("paragraph.line_block")
        if context.supports("paragraph.fenced_div"):
            candidates.append("paragraph.fenced_div")
        if context.supports("theorem.block"):
            candidates.append("theorem.block")
        if context.supports("inline.abbreviation.definition"):
            candidates.append("inline.abbreviation.definition")
        if not candidates or context.rng.random() >= options.block_ratio:
            return None
        chosen = context.weighted_feature(candidates)
        if chosen == "paragraph.line_block":
            lines = tuple(
                (Text(context.text.phrase(min_words=2, max_words=5)),)
                for _ in range(context.text.number(2, 4))
            )
            return LineBlock(lines=lines)
        if chosen == "paragraph.fenced_div":
            classes = (context.text.word(),)
            return FencedDiv(
                children=(Paragraph(children=(Text(context.text.sentence()),)),),
                info=classes[0],
                attributes=Attributes(classes=classes),
            )
        if chosen == "theorem.block":
            title = context.text.phrase(min_words=2, max_words=5, title_case=True)
            return FencedDiv(
                children=(Paragraph(children=(Text(context.text.sentence()),)),),
                attributes=Attributes(classes=("theorem",), pairs=(("title", title),)),
            )
        label = context.text.word(min_length=3, max_length=5).upper()
        title = context.text.phrase(min_words=3, max_words=7, title_case=True)
        return AbbreviationDefinition(label=label, title=title)

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

    def _sentence(self, context: GenerationContext, options: ParagraphOptions) -> str:
        return context.text.sentence(
            min_words=options.sentence_min_words,
            max_words=options.sentence_max_words,
        )

    def _decorate(
        self,
        context: GenerationContext,
        builder: Callable[[str], InlineNode],
        options: ParagraphOptions,
    ) -> tuple[InlineNode, ...]:
        sentence = self._sentence(context, options)
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
