"""Validated, immutable specifications for a generation run."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from dummy_md.core.budget import Mode, Unit
from dummy_md.core.dialects import DIALECTS
from dummy_md.exceptions import ConfigurationError, DialectError
from dummy_md.text import TEXT_PROVIDERS


@dataclass(frozen=True, slots=True)
class LengthSpec:
    """How much output to produce."""

    value: int
    unit: Unit = "chars"
    mode: Mode = "approximate"
    tolerance: float = 0.05

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ConfigurationError("length value must be non-negative")
        if self.unit not in {"chars", "words", "lines", "blocks", "bytes"}:
            raise ConfigurationError(f"unknown length unit {self.unit!r}")
        if self.mode not in {"approximate", "exact"}:
            raise ConfigurationError(f"unknown length mode {self.mode!r}")
        if not 0 <= self.tolerance <= 1:
            raise ConfigurationError("tolerance must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ElementRule:
    """Per-family counts, weight, and generator options."""

    min_count: int = 0
    max_count: int | None = None
    weight: float = 1.0
    options: object = None

    def __post_init__(self) -> None:
        if self.min_count < 0:
            raise ConfigurationError("min_count must be non-negative")
        if self.max_count is not None and self.max_count < self.min_count:
            raise ConfigurationError("max_count must be >= min_count")
        if self.weight <= 0:
            raise ConfigurationError("element weight must be positive")


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    """Everything needed to reproduce a document byte for byte."""

    dialect: str = "gfm"
    seed: int = 0
    length: LengthSpec = field(default_factory=lambda: LengthSpec(1000))
    include: Sequence[str] = ()
    exclude: Sequence[str] = ()
    elements: Mapping[str, ElementRule] = field(
        default_factory=lambda: MappingProxyType({})
    )
    text_style: str = "pseudowords"
    max_nesting_depth: int = 3
    heading_skeleton: bool = True
    include_frontmatter: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "include", tuple(self.include))
        object.__setattr__(self, "exclude", tuple(self.exclude))
        if self.dialect not in DIALECTS:
            raise DialectError(
                f"unknown dialect {self.dialect!r}", dialects=sorted(DIALECTS)
            )
        if self.text_style not in TEXT_PROVIDERS:
            raise ConfigurationError(
                f"unknown text style {self.text_style!r}; "
                f"choose from {', '.join(sorted(TEXT_PROVIDERS))}"
            )
        if self.max_nesting_depth < 1:
            raise ConfigurationError("max_nesting_depth must be at least 1")
        for pattern in (*self.include, *self.exclude):
            if not pattern:
                raise ConfigurationError("feature patterns must not be empty")
        for family, rule in self.elements.items():
            if not family:
                raise ConfigurationError("element family names must not be empty")
            if not isinstance(rule, ElementRule):
                raise ConfigurationError(
                    f"element rule for {family!r} is not an ElementRule"
                )
