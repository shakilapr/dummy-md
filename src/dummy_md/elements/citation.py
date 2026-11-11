"""Citation generation: Pandoc citations and bibliography scaffolding."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    Bibliography,
    BlockNode,
    Citation,
    FrontMatter,
    Paragraph,
    Text,
)
from dummy_md.elements._util import check_ratio, resolve_options

_CITATION_FEATURES = (
    "citation.bracketed",
    "citation.multiple",
    "citation.narrative",
    "citation.suppress_author",
    "citation.locator",
)

_BIBLIOGRAPHY_FEATURES = (
    "citation.bibliography_resource",
    "citation.bibliography_nocite",
    "citation.bibliography_directive",
)


@dataclass(frozen=True, slots=True)
class CitationOptions:
    bibliography_ratio: float = 0.25
    prefix_ratio: float = 0.3
    locator_ratio: float = 0.4

    def __post_init__(self) -> None:
        for name in ("bibliography_ratio", "prefix_ratio", "locator_ratio"):
            check_ratio(getattr(self, name), name)


class CitationGenerator:
    family = "citation"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, CitationOptions(), CitationOptions
        )
        bibliography = [
            feature
            for feature in context.active_in_family("citation")
            if feature in _BIBLIOGRAPHY_FEATURES
        ]
        if bibliography and (
            not context.supports_any(_CITATION_FEATURES)
            or context.rng.random() < options.bibliography_ratio
        ):
            feature = context.weighted_feature(bibliography)
            if feature == "citation.bibliography_directive":
                return Bibliography(feature=feature, kind="directive")
            if feature == "citation.bibliography_nocite":
                return FrontMatter(format="yaml", content="nocite: '@*'")
            return FrontMatter(format="yaml", content="bibliography: references.bib")

        candidates = [
            feature
            for feature in context.active_in_family("citation")
            if feature in _CITATION_FEATURES
        ]
        feature = context.weighted_feature(candidates)
        keys = (
            tuple(context.text.word() for _ in range(context.rng.randint(2, 3)))
            if feature == "citation.multiple"
            else (context.text.word(),)
        )
        prefix = "See" if context.rng.random() < options.prefix_ratio else ""
        locator = (
            f"p. {context.text.number(1, 240)}"
            if feature in {"citation.locator", "citation.bracketed"}
            and context.rng.random() < options.locator_ratio
            else ""
        )
        narrative = feature == "citation.narrative"
        citation = Citation(
            feature=feature,
            keys=keys,
            mode="narrative" if narrative else "bracketed",
            prefix="" if narrative else prefix,
            locator=locator,
            suppress_author=feature == "citation.suppress_author",
        )
        if narrative:
            lead = "According to " if not prefix else prefix + " "
            return Paragraph(children=(Text(lead), citation, Text(".")))
        return Paragraph(children=(citation, Text(".")))
