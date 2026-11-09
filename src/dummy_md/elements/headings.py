"""Heading generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import Attributes, BlockNode, Heading, InlineNode, Text
from dummy_md.elements._util import resolve_options


@dataclass(frozen=True, slots=True)
class HeadingOptions:
    levels: tuple[int, ...] = (1, 2, 3, 4)
    style: Literal["atx", "setext", "random"] = "random"
    closed: bool = False
    closed_ratio: float = 0.5
    setext_ratio: float = 0.25
    allow_skips: bool = False
    attribute_ratio: float = 0.2
    repeat_ratio: float = 0.12


class HeadingGenerator:
    """Produces ATX and Setext headings with optional attributes."""

    family = "heading"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, HeadingOptions(), HeadingOptions
        )
        levels = self._levels(context, options)
        desired = context.rng.choice(levels)
        level = context.headings.next_level(
            desired,
            allow_skips=options.allow_skips
            or context.supports("heading.levels.skipped"),
        )
        level = min(level, 6)

        text = context.text.heading_phrase(level)
        if (
            options.repeat_ratio
            and context.supports("heading.titles.repeated")
            and context.headings.last_title
            and context.rng.random() < options.repeat_ratio
        ):
            text = context.headings.last_title
        context.headings.record(level)
        context.headings.last_title = text

        style = self._style(context, options, level)
        closed = options.closed and context.rng.random() < options.closed_ratio
        attributes = self._attributes(context, options)
        return Heading(
            level=level,
            children=self._children(context, text),
            style=style,
            closed=closed,
            attributes=attributes,
        )

    # -- helpers ----------------------------------------------------------
    def _levels(
        self, context: GenerationContext, options: HeadingOptions
    ) -> tuple[int, ...]:
        supported = tuple(
            level
            for level in range(1, 7)
            if context.supports(f"heading.atx.h{level}")
            or context.supports(f"heading.setext.h{level}")
        )
        preferred = tuple(level for level in options.levels if level in supported)
        return preferred or supported or (1, 2, 3)

    def _style(
        self, context: GenerationContext, options: HeadingOptions, level: int
    ) -> Literal["atx", "setext"]:
        setext_ok = level <= 2 and context.supports(f"heading.setext.h{level}")
        atx_ok = context.supports(f"heading.atx.h{level}")
        if options.style == "setext" and setext_ok:
            return "setext"
        if options.style == "atx" and atx_ok:
            return "atx"
        if setext_ok and (not atx_ok or context.rng.random() < options.setext_ratio):
            return "setext"
        return "atx"

    def _children(
        self, context: GenerationContext, text: str
    ) -> tuple[InlineNode, ...]:
        if context.supports("heading.atx.closing") and context.rng.random() < 0.2:
            return (Text(text + " "),)
        return (Text(text),)

    def _attributes(
        self, context: GenerationContext, options: HeadingOptions
    ) -> Attributes | None:
        if not context.supports("heading.attributes.identifier"):
            return None
        if context.rng.random() >= options.attribute_ratio:
            return None
        identifier = context.text.identifier(style="kebab-case")
        classes: tuple[str, ...] = ()
        if (
            context.supports("heading.attributes.classes")
            and context.rng.random() < 0.5
        ):
            classes = (context.text.word(min_length=3, max_length=8),)
        return Attributes(identifier=identifier, classes=classes)
