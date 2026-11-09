"""Shared helpers for element generators."""

from __future__ import annotations

from typing import TypeVar

from dummy_md.config import ElementRule
from dummy_md.core.context import GenerationContext
from dummy_md.exceptions import ConfigurationError

T = TypeVar("T")


def resolve_options(
    context: GenerationContext, family: str, default: T, option_type: type[T]
) -> T:
    """Return the caller's options object for ``family`` or the built-in default."""
    rule: ElementRule | None = context.options.get(family)
    if rule is None or rule.options is None:
        return default
    if isinstance(rule.options, option_type):
        return rule.options
    raise ConfigurationError(
        f"options for {family!r} must be {option_type.__name__}, "
        f"got {type(rule.options).__name__}"
    )
