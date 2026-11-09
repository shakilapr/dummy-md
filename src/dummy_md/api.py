"""Functional public API."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dummy_md.config import DocumentSpec, ElementRule, LengthSpec
from dummy_md.core.budget import Mode, Unit
from dummy_md.core.engine import Generator
from dummy_md.core.registry import registry
from dummy_md.exceptions import ConfigurationError
from dummy_md.presets import describe as describe_presets
from dummy_md.presets import get as get_preset

ElementRules = Mapping[str, ElementRule]


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
    include: Sequence[str],
    exclude: Sequence[str],
    elements: ElementRules | None,
    text_style: str,
    max_nesting_depth: int,
    mode: Mode,
    tolerance: float,
    preset: str | None,
) -> DocumentSpec:
    spec = DocumentSpec(
        dialect=dialect,
        seed=seed,
        length=LengthSpec(value=length, unit=unit, mode=mode, tolerance=tolerance),
        include=tuple(include),
        exclude=tuple(exclude),
        elements=elements or {},
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
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
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    elements: ElementRules | None = None,
    text_style: str = "pseudowords",
    max_nesting_depth: int = 3,
    mode: Mode = "approximate",
    tolerance: float = 0.05,
    preset: str | None = None,
) -> str:
    """Generate a Markdown document and return it as a string."""
    spec = _spec(
        length=length,
        unit=unit,
        dialect=dialect,
        seed=seed,
        include=include,
        exclude=exclude,
        elements=elements,
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
        mode=mode,
        tolerance=tolerance,
        preset=preset,
    )
    return Generator(spec).generate()


def iter_chunks(
    *,
    length: int = 1000,
    unit: Unit = "chars",
    dialect: str = "gfm",
    seed: int = 0,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    elements: ElementRules | None = None,
    text_style: str = "pseudowords",
    max_nesting_depth: int = 3,
    mode: Mode = "approximate",
    tolerance: float = 0.05,
    preset: str | None = None,
    chunk_size: int | None = None,
) -> Iterator[str]:
    """Stream a generated document in section-sized chunks."""
    spec = _spec(
        length=length,
        unit=unit,
        dialect=dialect,
        seed=seed,
        include=include,
        exclude=exclude,
        elements=elements,
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
        mode=mode,
        tolerance=tolerance,
        preset=preset,
    )
    yield from Generator(spec).iter_chunks(chunk_size)


def write(
    path: str | Path,
    *,
    length: int = 1000,
    unit: Unit = "chars",
    dialect: str = "gfm",
    seed: int = 0,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    elements: ElementRules | None = None,
    text_style: str = "pseudowords",
    max_nesting_depth: int = 3,
    mode: Mode = "approximate",
    tolerance: float = 0.05,
    preset: str | None = None,
) -> Path:
    """Generate a document directly into ``path`` and return the path."""
    spec = _spec(
        length=length,
        unit=unit,
        dialect=dialect,
        seed=seed,
        include=include,
        exclude=exclude,
        elements=elements,
        text_style=text_style,
        max_nesting_depth=max_nesting_depth,
        mode=mode,
        tolerance=tolerance,
        preset=preset,
    )
    return Generator(spec).write(path)


def available_elements(dialect: str | None = None) -> tuple[str, ...]:
    """Implemented feature ids, optionally filtered to one dialect."""
    features = registry.features
    if dialect is None:
        return tuple(sorted(spec.id for spec in features.values() if spec.implemented))
    resolved = registry.dialect(dialect)
    return tuple(sorted(resolved.features))


def available_dialects() -> tuple[str, ...]:
    return registry.dialect_names()


def available_presets() -> Mapping[str, str]:
    return describe_presets()


def validate(text: str, dialect: str = "gfm") -> ValidationReport:
    """Parse ``text`` with markdown-it-py, if the development extra is installed."""
    registry.dialect(dialect)
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
