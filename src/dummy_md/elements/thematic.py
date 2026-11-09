"""Thematic break generation."""

from __future__ import annotations

from typing import Literal

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, ThematicBreak

_CHARACTERS: dict[str, Literal["-", "*", "_"]] = {
    "thematic_break.hyphen": "-",
    "thematic_break.asterisk": "*",
    "thematic_break.underscore": "_",
}


class ThematicBreakGenerator:
    family = "thematic_break"

    def generate(self, context: GenerationContext) -> BlockNode:
        choices: list[Literal["-", "*", "_"]] = [
            character
            for feature, character in _CHARACTERS.items()
            if context.supports(feature)
        ]
        character: Literal["-", "*", "_"] = (
            context.rng.choice(choices) if choices else "-"
        )
        spacing = context.rng.choice((0, 0, 0, 1, 2))
        return ThematicBreak(character=character, spacing=spacing)
