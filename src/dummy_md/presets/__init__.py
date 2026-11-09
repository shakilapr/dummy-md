"""Built-in generation presets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from dummy_md.config import DocumentSpec, ElementRule
from dummy_md.elements import TableOptions
from dummy_md.exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class Preset:
    """A named set of feature choices layered onto a :class:`DocumentSpec`."""

    name: str
    description: str
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    text_style: str = "pseudowords"
    dialect: str = ""
    max_nesting_depth: int = 3
    elements: Mapping[str, ElementRule] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def apply(self, spec: DocumentSpec) -> DocumentSpec:
        return replace(
            spec,
            include=self.include or spec.include,
            exclude=self.exclude or spec.exclude,
            text_style=self.text_style or spec.text_style,
            dialect=self.dialect or spec.dialect,
            max_nesting_depth=self.max_nesting_depth,
            elements=self.elements or spec.elements,
        )


PRESETS: dict[str, Preset] = {
    "default": Preset(
        name="default",
        description="Balanced mix of every feature the dialect supports",
    ),
    "minimal": Preset(
        name="minimal",
        description="Headings, paragraphs and rules only; classic lorem text",
        include=("heading.*", "paragraph.*", "thematic_break.*"),
        text_style="lorem",
        max_nesting_depth=1,
    ),
    "readme": Preset(
        name="readme",
        description="README-shaped document: headings, lists, code and links",
        include=(
            "heading.*",
            "paragraph.*",
            "list.*",
            "code.*",
            "link.*",
            "image.*",
            "table.pipe",
            "table.align.*",
        ),
        exclude=("html.*",),
        max_nesting_depth=2,
        elements=MappingProxyType(
            {
                "paragraph": ElementRule(weight=8),
                "heading": ElementRule(min_count=2, weight=3),
                "code": ElementRule(weight=3),
            }
        ),
    ),
    "tables": Preset(
        name="tables",
        description="Table-heavy fixtures with numeric cells",
        include=("heading.*", "paragraph.*", "table.*"),
        exclude=("table.rows.many", "table.columns.many"),
        elements=MappingProxyType(
            {
                "table": ElementRule(
                    min_count=1,
                    weight=10,
                    options=TableOptions(
                        min_rows=2,
                        max_rows=4,
                        min_columns=2,
                        max_columns=3,
                        min_cell_words=1,
                        max_cell_words=2,
                    ),
                ),
                "paragraph": ElementRule(weight=4),
            }
        ),
    ),
    "stress": Preset(
        name="stress",
        description="Large nested documents with token text for parser stress",
        dialect="stress",
        text_style="tokens",
        max_nesting_depth=5,
    ),
}


def get(name: str) -> Preset:
    preset = PRESETS.get(name)
    if preset is None:
        raise ConfigurationError(
            f"unknown preset {name!r}; choose from {', '.join(sorted(PRESETS))}"
        )
    return preset


def register_preset(preset: Preset, *, replace: bool = False) -> None:
    """Make a custom preset available by name to ``generate(preset=...)``."""
    if not preset.name:
        raise ConfigurationError("preset name must not be empty")
    if preset.name in PRESETS and not replace:
        raise ConfigurationError(f"preset {preset.name!r} is already registered")
    PRESETS[preset.name] = preset


def describe() -> Mapping[str, str]:
    return MappingProxyType(
        {preset.name: preset.description for preset in PRESETS.values()}
    )
