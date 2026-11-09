"""Shared helpers for element generators."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from typing import TypeVar

from dummy_md.config import ElementRule
from dummy_md.core.context import GenerationContext
from dummy_md.exceptions import ConfigurationError

T = TypeVar("T")


def resolve_options(
    context: GenerationContext, family: str, default: T, option_type: type[T]
) -> T:
    """Return the caller's options for ``family``.

    Accepts either a constructed options dataclass or a plain mapping (as loaded
    from a JSON spec); mappings are validated against the dataclass fields.
    """
    rule: ElementRule | None = context.options.get(family)
    if rule is None or rule.options is None:
        return default
    if isinstance(rule.options, option_type):
        return rule.options
    if isinstance(rule.options, Mapping):
        return build_options(option_type, rule.options, family)
    raise ConfigurationError(
        f"options for {family!r} must be {option_type.__name__} or a mapping, "
        f"got {type(rule.options).__name__}"
    )


def build_options(
    option_type: type[T], data: Mapping[str, object], family: str = "element"
) -> T:
    """Instantiate ``option_type`` from a mapping, rejecting unknown keys."""
    names = {item.name for item in fields(option_type)}  # type: ignore[arg-type]
    unknown = sorted(str(key) for key in data if str(key) not in names)
    if unknown:
        raise ConfigurationError(
            f"unknown option(s) for {family!r}: {', '.join(unknown)}; "
            f"valid options: {', '.join(sorted(names))}"
        )
    kwargs = {str(key): value for key, value in data.items()}
    try:
        return option_type(**kwargs)
    except TypeError as error:
        raise ConfigurationError(f"invalid options for {family!r}: {error}") from error
