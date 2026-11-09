"""Placeholder text generation, decoupled from Markdown syntax."""

from dummy_md.exceptions import ConfigurationError
from dummy_md.text.base import TextProvider
from dummy_md.text.engine import DummyContentEngine
from dummy_md.text.lorem import LOREM
from dummy_md.text.pseudowords import PSEUDOWORDS
from dummy_md.text.tokens import TOKENS

TEXT_PROVIDERS: dict[str, TextProvider] = {
    "pseudowords": PSEUDOWORDS,
    "lorem": LOREM,
    "tokens": TOKENS,
}


def register_text_style(
    name: str, provider: TextProvider, *, replace: bool = False
) -> None:
    """Register a custom word source under ``name``.

    Providers expose ``name`` and ``word(rng)``; sentence structure, casing and
    punctuation stay in the content engine, so custom styles inherit the same
    layout guarantees as the built-ins.
    """
    if not name:
        raise ConfigurationError("text style name must not be empty")
    if name in TEXT_PROVIDERS and not replace:
        raise ConfigurationError(f"text style {name!r} is already registered")
    if not isinstance(provider, TextProvider):
        raise ConfigurationError(
            f"text provider for {name!r} must define 'name' and 'word(rng)'"
        )
    TEXT_PROVIDERS[name] = provider


def text_provider(name: str) -> TextProvider:
    """Look up a registered word source, raising a clear error when unknown."""
    try:
        return TEXT_PROVIDERS[name]
    except KeyError:
        raise ConfigurationError(
            f"unknown text style {name!r}; choose from {', '.join(text_styles())}"
        ) from None


def text_styles() -> tuple[str, ...]:
    return tuple(sorted(TEXT_PROVIDERS))


__all__ = [
    "DummyContentEngine",
    "LOREM",
    "PSEUDOWORDS",
    "TEXT_PROVIDERS",
    "TOKENS",
    "register_text_style",
    "text_provider",
    "text_styles",
]
