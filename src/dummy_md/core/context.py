"""Per-run generation state shared by every generator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from random import Random
from typing import TYPE_CHECKING

from dummy_md.core.budget import BudgetTracker
from dummy_md.core.dialects import Dialect
from dummy_md.core.nodes import FootnoteDefinition, LinkDefinition
from dummy_md.text.engine import DummyContentEngine

if TYPE_CHECKING:
    from dummy_md.config import ElementRule


@dataclass(slots=True)
class HeadingTracker:
    """Keeps heading levels from jumping past one step."""

    last_level: int = 0
    last_title: str = ""
    seen: list[int] = field(default_factory=list)

    def next_level(self, desired: int, *, allow_skips: bool = False) -> int:
        level = max(1, min(6, desired))
        if allow_skips or not self.last_level:
            return level
        return min(level, self.last_level + 1)

    def record(self, level: int) -> None:
        self.last_level = level
        self.seen.append(level)

    def reset(self) -> None:
        self.last_level = 0
        self.seen.clear()


@dataclass(slots=True)
class ReferenceRegistry:
    """Link and footnote definitions collected during generation."""

    links: dict[str, LinkDefinition] = field(default_factory=dict)
    footnotes: dict[str, FootnoteDefinition] = field(default_factory=dict)
    _footnote_counter: int = 0
    _link_counter: int = 0

    def add_link(self, definition: LinkDefinition) -> LinkDefinition:
        existing = self.links.get(definition.label)
        if existing is not None:
            return existing
        self.links[definition.label] = definition
        return definition

    def add_footnote(self, definition: FootnoteDefinition) -> FootnoteDefinition:
        existing = self.footnotes.get(definition.label)
        if existing is not None:
            return existing
        self.footnotes[definition.label] = definition
        return definition

    def footnote_label(self) -> str:
        self._footnote_counter += 1
        return str(self._footnote_counter)

    def link_label(self, prefix: str = "ref") -> str:
        self._link_counter += 1
        return f"{prefix}-{self._link_counter}"


@dataclass(slots=True)
class GenerationContext:
    """Mutable run state; AST nodes built from it stay immutable."""

    rng: Random
    dialect: Dialect
    text: DummyContentEngine
    active_features: frozenset[str]
    budget: BudgetTracker
    options: Mapping[str, ElementRule] = field(default_factory=dict)
    depth: int = 0
    max_depth: int = 3
    headings: HeadingTracker = field(default_factory=HeadingTracker)
    refs: ReferenceRegistry = field(default_factory=ReferenceRegistry)
    block_hint: int = 480

    def supports(self, feature_id: str) -> bool:
        return feature_id in self.active_features

    def supports_any(self, feature_ids: tuple[str, ...]) -> bool:
        return any(feature_id in self.active_features for feature_id in feature_ids)

    def active_in_family(self, family: str) -> tuple[str, ...]:
        prefix = family + "."
        return tuple(
            sorted(
                feature
                for feature in self.active_features
                if feature.startswith(prefix)
            )
        )

    @property
    def can_nest(self) -> bool:
        return self.depth < self.max_depth

    def nested(self) -> GenerationContext:
        """A view one nesting level deeper, sharing RNG, trackers, and budget."""
        return replace(self, depth=self.depth + 1)
