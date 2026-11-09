"""Thematic break generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, ThematicBreak
from dummy_md.elements._util import resolve_options

_CHARACTERS: dict[str, Literal["-", "*", "_"]] = {
    "thematic_break.hyphen": "-",
    "thematic_break.asterisk": "*",
    "thematic_break.underscore": "_",
}


@dataclass(frozen=True, slots=True)
class ThematicBreakOptions:
    spacings: tuple[int, ...] = (0, 0, 0, 1, 2)


class ThematicBreakGenerator:
    family = "thematic_break"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, ThematicBreakOptions(), ThematicBreakOptions
        )
        candidates = [feature for feature in _CHARACTERS if context.supports(feature)]
        feature = context.weighted_feature(candidates) if candidates else None
        character: Literal["-", "*", "_"] = (
            _CHARACTERS[feature] if feature is not None else "-"
        )
        spacings = options.spacings or (0,)
        return ThematicBreak(character=character, spacing=context.rng.choice(spacings))


__all__ = ["ThematicBreakGenerator", "ThematicBreakOptions"]
