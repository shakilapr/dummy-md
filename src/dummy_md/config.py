"""Validated, immutable specifications for a generation run."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from types import MappingProxyType
from typing import Any, Literal, cast

from dummy_md.core.budget import Mode, Unit
from dummy_md.exceptions import ConfigurationError
from dummy_md.text import TEXT_PROVIDERS

LineEnding = Literal["lf", "crlf"]


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

    def to_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "unit": self.unit,
            "mode": self.mode,
            "tolerance": self.tolerance,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> LengthSpec:
        _reject_unknown(data, {"value", "unit", "mode", "tolerance"}, "length")
        return cls(
            value=_as_int(data.get("value", 1000), "length.value"),
            unit=cast(Unit, _as_str(data.get("unit", "chars"), "length.unit")),
            mode=cast(Mode, _as_str(data.get("mode", "approximate"), "length.mode")),
            tolerance=_as_float(data.get("tolerance", 0.05), "length.tolerance"),
        )


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

    def to_dict(self) -> dict[str, object]:
        return {
            "min_count": self.min_count,
            "max_count": self.max_count,
            "weight": self.weight,
            "options": _options_to_dict(self.options),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ElementRule:
        _reject_unknown(
            data, {"min_count", "max_count", "weight", "options"}, "element rule"
        )
        raw_max = data.get("max_count")
        return cls(
            min_count=_as_int(data.get("min_count", 0), "min_count"),
            max_count=None if raw_max is None else _as_int(raw_max, "max_count"),
            weight=_as_float(data.get("weight", 1.0), "weight"),
            options=data.get("options"),
        )


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    """Everything needed to reproduce a document byte for byte."""

    dialect: str = "gfm"
    seed: int = 0
    text_seed: int | None = None
    length: LengthSpec = field(default_factory=lambda: LengthSpec(1000))
    include: Sequence[str] = ()
    exclude: Sequence[str] = ()
    elements: Mapping[str, ElementRule] = field(
        default_factory=lambda: MappingProxyType({})
    )
    feature_weights: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType({})
    )
    text_style: str = "pseudowords"
    max_nesting_depth: int = 3
    heading_skeleton: bool = True
    include_frontmatter: bool = True
    line_ending: LineEnding = "lf"
    trailing_newline: bool = True
    section_chars: int = 16_000
    fill_ratio: float = 0.9

    def __post_init__(self) -> None:
        object.__setattr__(self, "include", tuple(self.include))
        object.__setattr__(self, "exclude", tuple(self.exclude))
        if not self.dialect:
            raise ConfigurationError("dialect must not be empty")
        if self.text_style not in TEXT_PROVIDERS:
            raise ConfigurationError(
                f"unknown text style {self.text_style!r}; "
                f"choose from {', '.join(sorted(TEXT_PROVIDERS))}"
            )
        if self.max_nesting_depth < 1:
            raise ConfigurationError("max_nesting_depth must be at least 1")
        if self.line_ending not in {"lf", "crlf"}:
            raise ConfigurationError(f"unknown line ending {self.line_ending!r}")
        if self.section_chars < 500:
            raise ConfigurationError("section_chars must be at least 500")
        if not 0 < self.fill_ratio <= 1.0:
            raise ConfigurationError("fill_ratio must be between 0 and 1")
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
        for feature_id, weight in self.feature_weights.items():
            if not feature_id:
                raise ConfigurationError("feature weight keys must not be empty")
            if weight <= 0:
                raise ConfigurationError(
                    f"feature weight for {feature_id!r} must be positive"
                )

    # -- serialization ----------------------------------------------------
    def to_dict(self) -> dict[str, object]:
        """A JSON-serializable representation that round-trips through from_dict."""
        return {
            "dialect": self.dialect,
            "seed": self.seed,
            "text_seed": self.text_seed,
            "length": self.length.to_dict(),
            "include": list(self.include),
            "exclude": list(self.exclude),
            "elements": {
                family: rule.to_dict() for family, rule in self.elements.items()
            },
            "feature_weights": dict(self.feature_weights),
            "text_style": self.text_style,
            "max_nesting_depth": self.max_nesting_depth,
            "heading_skeleton": self.heading_skeleton,
            "include_frontmatter": self.include_frontmatter,
            "line_ending": self.line_ending,
            "trailing_newline": self.trailing_newline,
            "section_chars": self.section_chars,
            "fill_ratio": self.fill_ratio,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> DocumentSpec:
        _reject_unknown(
            data,
            {
                "dialect",
                "seed",
                "text_seed",
                "length",
                "include",
                "exclude",
                "elements",
                "feature_weights",
                "text_style",
                "max_nesting_depth",
                "heading_skeleton",
                "include_frontmatter",
                "line_ending",
                "trailing_newline",
                "section_chars",
                "fill_ratio",
            },
            "spec",
        )
        raw_length = data.get("length", {})
        length = (
            LengthSpec.from_dict(cast(Mapping[str, object], raw_length))
            if isinstance(raw_length, Mapping)
            else cls._bad("length", "an object")
        )
        raw_elements = data.get("elements", {})
        elements: dict[str, ElementRule] = {}
        if isinstance(raw_elements, Mapping):
            for family, raw_rule in raw_elements.items():
                if not isinstance(raw_rule, Mapping):
                    raise ConfigurationError(
                        f"element rule for {family!r} must be an object"
                    )
                elements[str(family)] = ElementRule.from_dict(
                    cast(Mapping[str, object], raw_rule)
                )
        else:
            raise ConfigurationError("elements must be an object")

        raw_weights = data.get("feature_weights", {})
        weights: dict[str, float] = {}
        if isinstance(raw_weights, Mapping):
            for feature_id, weight in raw_weights.items():
                weights[str(feature_id)] = _as_float(
                    weight, f"feature_weights.{feature_id}"
                )
        else:
            raise ConfigurationError("feature_weights must be an object")

        raw_seed = data.get("text_seed")
        return cls(
            dialect=_as_str(data.get("dialect", "gfm"), "dialect"),
            seed=_as_int(data.get("seed", 0), "seed"),
            text_seed=None if raw_seed is None else _as_int(raw_seed, "text_seed"),
            length=length,
            include=_as_str_list(data.get("include", []), "include"),
            exclude=_as_str_list(data.get("exclude", []), "exclude"),
            elements=elements,
            feature_weights=weights,
            text_style=_as_str(data.get("text_style", "pseudowords"), "text_style"),
            max_nesting_depth=_as_int(
                data.get("max_nesting_depth", 3), "max_nesting_depth"
            ),
            heading_skeleton=_as_bool(
                data.get("heading_skeleton", True), "heading_skeleton"
            ),
            include_frontmatter=_as_bool(
                data.get("include_frontmatter", True), "include_frontmatter"
            ),
            line_ending=cast(
                LineEnding, _as_str(data.get("line_ending", "lf"), "line_ending")
            ),
            trailing_newline=_as_bool(
                data.get("trailing_newline", True), "trailing_newline"
            ),
            section_chars=_as_int(data.get("section_chars", 16_000), "section_chars"),
            fill_ratio=_as_float(data.get("fill_ratio", 0.9), "fill_ratio"),
        )

    @staticmethod
    def _bad(name: str, expected: str) -> Any:
        raise ConfigurationError(f"{name} must be {expected}")


# --------------------------------------------------------------------------
# Coercion helpers (JSON values are untyped)
# --------------------------------------------------------------------------


def _reject_unknown(
    data: Mapping[str, object], allowed: set[str], context: str
) -> None:
    unknown = sorted(str(key) for key in data if str(key) not in allowed)
    if unknown:
        raise ConfigurationError(f"unknown key(s) in {context}: {', '.join(unknown)}")


def _as_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer")
    return value


def _as_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number")
    return float(value)


def _as_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a boolean")
    return value


def _as_str(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string")
    return value


def _as_str_list(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ConfigurationError(f"{name} must be a list of strings")
    items: list[str] = []
    for item in value:
        items.append(_as_str(item, name))
    return tuple(items)


def _options_to_dict(options: object) -> object:
    if options is None:
        return None
    if isinstance(options, Mapping):
        return {str(key): _jsonable(value) for key, value in options.items()}
    if is_dataclass(options) and not isinstance(options, type):
        return _jsonable(asdict(options))
    raise ConfigurationError(
        f"options must be a dataclass or mapping, got {type(options).__name__}"
    )


def _jsonable(value: object) -> object:
    """Normalize nested tuples/dataclasses into JSON-friendly structures."""
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    return value
