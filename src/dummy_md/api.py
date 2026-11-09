"""Functional public API."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dummy_md.config import DocumentSpec, ElementRule, LengthSpec, LineEnding
from dummy_md.core.budget import Mode, Unit
from dummy_md.core.engine import Generator
from dummy_md.core.registry import Registry
from dummy_md.core.registry import registry as default_registry
from dummy_md.exceptions import ConfigurationError
from dummy_md.presets import describe as describe_presets
from dummy_md.presets import get as get_preset

ElementRules = Mapping[str, ElementRule]
FeatureWeights = Mapping[str, float]


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Result of an optional parser verification pass."""

    dialect: str
    ok: bool
    tokens: int
    errors: tuple[str, ...] = ()


def _spec(
    *,
    length: int,
    unit: Unit,
    dialect: str,
    seed: int,
    text_seed: int | None,
    include: Sequence[str],
    exclude: Sequence[str],
    elements: ElementRules | None,
    feature_weights: FeatureWeights | None,
    text_style: str,
    max_nesting_depth: int,
    mode: Mode,
    tolerance: float,
    preset: str | None,
    heading_skeleton: bool,
    include_frontmatter: bool,
    line_ending: LineEnding,
    trailing_newline: bool,
    section_chars: int,
    fill_ratio: float,
) -> DocumentSpec:
    spec = DocumentSpec(
        dialect=dialect,
        seed=seed,
        text_seed=text_seed,
        length=LengthSpec(value=length, unit=unit, mode=mode, tolerance=tolerance),
        include=tuple(include),
        exclude=tuple(exclude),
        elements=elements or {},
        feature_weights=feature_weights or {},
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
        heading_skeleton=heading_skeleton,
        include_frontmatter=include_frontmatter,
        line_ending=line_ending,
        trailing_newline=trailing_newline,
        section_chars=section_chars,
        fill_ratio=fill_ratio,
    )
    if preset is not None:
        spec = get_preset(preset).apply(spec)
    return spec


def generate(
    *,
    length: int = 1000,
    unit: Unit = "chars",
    dialect: str = "gfm",
    seed: int = 0,
    text_seed: int | None = None,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    elements: ElementRules | None = None,
    feature_weights: FeatureWeights | None = None,
    text_style: str = "pseudowords",
    max_nesting_depth: int = 3,
    mode: Mode = "approximate",
    tolerance: float = 0.05,
    preset: str | None = None,
    heading_skeleton: bool = True,
    include_frontmatter: bool = True,
    line_ending: LineEnding = "lf",
    trailing_newline: bool = True,
    section_chars: int = 16_000,
    fill_ratio: float = 0.9,
    registry: Registry | None = None,
) -> str:
    """Generate a Markdown document and return it as a string."""
    spec = _spec(
        length=length,
        unit=unit,
        dialect=dialect,
        seed=seed,
        text_seed=text_seed,
        include=include,
        exclude=exclude,
        elements=elements,
        feature_weights=feature_weights,
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
        mode=mode,
        tolerance=tolerance,
        preset=preset,
        heading_skeleton=heading_skeleton,
        include_frontmatter=include_frontmatter,
        line_ending=line_ending,
        trailing_newline=trailing_newline,
        section_chars=section_chars,
        fill_ratio=fill_ratio,
    )
    return Generator(spec, registry).generate()


def iter_chunks(
    *,
    length: int = 1000,
    unit: Unit = "chars",
    dialect: str = "gfm",
    seed: int = 0,
    text_seed: int | None = None,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    elements: ElementRules | None = None,
    feature_weights: FeatureWeights | None = None,
    text_style: str = "pseudowords",
    max_nesting_depth: int = 3,
    mode: Mode = "approximate",
    tolerance: float = 0.05,
    preset: str | None = None,
    heading_skeleton: bool = True,
    include_frontmatter: bool = True,
    line_ending: LineEnding = "lf",
    trailing_newline: bool = True,
    section_chars: int = 16_000,
    fill_ratio: float = 0.9,
    chunk_size: int | None = None,
    registry: Registry | None = None,
) -> Iterator[str]:
    """Stream a generated document in section-sized chunks."""
    spec = _spec(
        length=length,
        unit=unit,
        dialect=dialect,
        seed=seed,
        text_seed=text_seed,
        include=include,
        exclude=exclude,
        elements=elements,
        feature_weights=feature_weights,
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
        mode=mode,
        tolerance=tolerance,
        preset=preset,
        heading_skeleton=heading_skeleton,
        include_frontmatter=include_frontmatter,
        line_ending=line_ending,
        trailing_newline=trailing_newline,
        section_chars=section_chars,
        fill_ratio=fill_ratio,
    )
    yield from Generator(spec, registry).iter_chunks(chunk_size)


def write(
    path: str | Path,
    *,
    length: int = 1000,
    unit: Unit = "chars",
    dialect: str = "gfm",
    seed: int = 0,
    text_seed: int | None = None,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    elements: ElementRules | None = None,
    feature_weights: FeatureWeights | None = None,
    text_style: str = "pseudowords",
    max_nesting_depth: int = 3,
    mode: Mode = "approximate",
    tolerance: float = 0.05,
    preset: str | None = None,
    heading_skeleton: bool = True,
    include_frontmatter: bool = True,
    line_ending: LineEnding = "lf",
    trailing_newline: bool = True,
    section_chars: int = 16_000,
    fill_ratio: float = 0.9,
    registry: Registry | None = None,
) -> Path:
    """Generate a document directly into ``path`` and return the path."""
    spec = _spec(
        length=length,
        unit=unit,
        dialect=dialect,
        seed=seed,
        text_seed=text_seed,
        include=include,
        exclude=exclude,
        elements=elements,
        feature_weights=feature_weights,
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
        mode=mode,
        tolerance=tolerance,
        preset=preset,
        heading_skeleton=heading_skeleton,
        include_frontmatter=include_frontmatter,
        line_ending=line_ending,
        trailing_newline=trailing_newline,
        section_chars=section_chars,
        fill_ratio=fill_ratio,
    )
    return Generator(spec, registry).write(path)


def available_elements(
    dialect: str | None = None, *, registry: Registry | None = None
) -> tuple[str, ...]:
    """Implemented feature ids, optionally filtered to one dialect."""
    active = registry if registry is not None else default_registry
    if dialect is None:
        return tuple(
            sorted(spec.id for spec in active.features.values() if spec.implemented)
        )
    return tuple(sorted(active.dialect(dialect).features))


def available_dialects(*, registry: Registry | None = None) -> tuple[str, ...]:
    active = registry if registry is not None else default_registry
    return active.dialect_names()


def available_presets() -> Mapping[str, str]:
    return describe_presets()


def validate(text: str, dialect: str = "gfm") -> ValidationReport:
    """Parse ``text`` with markdown-it-py, if the development extra is installed."""
    try:
        from markdown_it import MarkdownIt
    except ImportError as error:  # pragma: no cover - depends on optional extra
        raise ConfigurationError(
            "validate() requires the 'dev' extra (markdown-it-py)"
        ) from error

    parser = MarkdownIt("commonmark")
    if dialect != "commonmark":
        parser = parser.enable("table")
    errors: list[str] = []
    try:
        tokens = parser.parse(text)
    except Exception as error:  # noqa: BLE001 - report parser failures verbatim
        return ValidationReport(
            dialect=dialect, ok=False, tokens=0, errors=(str(error),)
        )
    if text and not tokens:
        errors.append("parser produced no tokens")
    if text.count("```") % 2 != 0:
        errors.append("unbalanced backtick fences")
    if text.count("~~~") % 2 != 0:
        errors.append("unbalanced tilde fences")
    return ValidationReport(
        dialect=dialect, ok=not errors, tokens=len(tokens), errors=tuple(errors)
    )
