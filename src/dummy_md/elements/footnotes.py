"""Footnote generation with a definition closure."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    BlockNode,
    FootnoteDefinition,
    FootnoteReference,
    Paragraph,
    Text,
)
from dummy_md.elements._util import check_ratio, resolve_options


@dataclass(frozen=True, slots=True)
class FootnoteOptions:
    multiline_ratio: float = 0.3

    def __post_init__(self) -> None:
        check_ratio(self.multiline_ratio, "multiline_ratio")


class FootnoteGenerator:
    family = "footnote"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, FootnoteOptions(), FootnoteOptions
        )
        if context.block_hint < 400:
            # A footnote definition adds an unavoidable document trailer; skip it
            # when the surrounding section budget is smaller than the trailer.
            return Paragraph(children=(Text(context.text.sentence()),))
        label = context.refs.footnote_label()
        body = Paragraph(
            children=(
                Text(context.text.sentence(min_words=5, max_words=12) + " "),
                FootnoteReference(label=label),
            )
        )
        children: list[BlockNode] = [
            Paragraph(children=(Text(context.text.sentence()),))
        ]
        if (
            context.supports("footnote.multiline")
            and context.rng.random() < options.multiline_ratio
        ):
            children.append(Paragraph(children=(Text(context.text.sentence()),)))
        context.refs.add_footnote(
            FootnoteDefinition(label=label, children=tuple(children))
        )
        return body
