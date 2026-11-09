"""Placeholder text generation, decoupled from Markdown syntax."""

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

__all__ = ["DummyContentEngine", "LOREM", "PSEUDOWORDS", "TOKENS", "TEXT_PROVIDERS"]
