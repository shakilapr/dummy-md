"""Planner: constraint-first, weighted-second block scheduling."""

from __future__ import annotations

from dummy_md.config import DocumentSpec, ElementRule
from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    BlockNode,
    Heading,
    Paragraph,
    Text,
)
from dummy_md.core.registry import Registry


class Planner:
    """Decides which generator runs next and enforces count constraints."""

    def __init__(
        self, context: GenerationContext, registry: Registry, spec: DocumentSpec
    ) -> None:
        self.context = context
        self.registry = registry
        self.spec = spec
        self.schedule = registry.schedule(context.active_features)
        self.families: tuple[str, ...] = tuple(sorted(self.schedule))
        self.counts: dict[str, int] = dict.fromkeys(self.families, 0)
        self.last_family: str | None = None
        self.frontmatter_emitted = False

    # -- constraints ------------------------------------------------------
    def rule(self, family: str) -> ElementRule:
        return self.spec.elements.get(family, ElementRule())

    def remaining_minimum(self) -> list[str]:
        return [
            family
            for family in self.families
            if self.counts[family] < self.rule(family).min_count
        ]

    def has_capacity(self, family: str) -> bool:
        maximum = self.rule(family).max_count
        return maximum is None or self.counts[family] < maximum

    def can_continue(self) -> bool:
        return bool(self.remaining_minimum()) or any(
            self.has_capacity(family) for family in self.families
        )

    # -- selection --------------------------------------------------------
    def choose(self) -> str | None:
        pending = self.remaining_minimum()
        if pending:
            return pending[0]
        candidates = [
            family
            for family in self.families
            if self.has_capacity(family) and family != self.last_family
        ]
        if not candidates:
            candidates = [
                family for family in self.families if self.has_capacity(family)
            ]
        if not candidates:
            return None
        weights = [self.rule(family).weight for family in candidates]
        return _weighted_choice(self.context, candidates, weights)

    def next_block(self) -> BlockNode | None:
        family = self.choose()
        if family is None:
            return None
        block = self.registry.generator(family).generate(self.context)
        self.counts[family] += 1
        self.last_family = family
        return block

    # -- structural skeleton ---------------------------------------------
    def skeleton(
        self,
        *,
        section_index: int,
        allow_frontmatter: bool = True,
        allow_title: bool = True,
    ) -> list[BlockNode]:
        blocks: list[BlockNode] = []
        if (
            section_index == 0
            and allow_frontmatter
            and self.spec.include_frontmatter
            and "frontmatter" in self.schedule
            and not self.frontmatter_emitted
        ):
            blocks.append(self.registry.generator("frontmatter").generate(self.context))
            self.frontmatter_emitted = True
        if (
            section_index == 0
            and allow_title
            and self.spec.heading_skeleton
            and "heading" in self.schedule
        ):
            title = self.context.text.heading_phrase(1)
            blocks.append(Heading(level=1, children=(Text(title),)))
            self.context.headings.record(1)
            self.context.headings.last_title = title
        return blocks


def _weighted_choice(
    context: GenerationContext, candidates: list[str], weights: list[float]
) -> str:
    total = sum(weights)
    threshold = context.rng.random() * total
    cumulative = 0.0
    for candidate, weight in zip(candidates, weights, strict=True):
        cumulative += weight
        if threshold < cumulative:
            return candidate
    return candidates[-1]


def filler_paragraph(context: GenerationContext) -> Paragraph:
    return Paragraph(children=(Text(context.text.sentence()),))
