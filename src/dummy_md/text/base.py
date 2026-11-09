"""Provider protocol and shared helpers for placeholder text."""

from __future__ import annotations

from random import Random
from typing import Protocol, runtime_checkable

VOWELS = "aeiou"
CONSONANTS = "bcdfghjklmnpqrstvwxyz"


@runtime_checkable
class TextProvider(Protocol):
    """A source of placeholder words.

    Providers are stateless: they receive the generator's RNG and return a single
    word in lowercase. Sentence structure, punctuation, and casing belong to
    :class:`~dummy_md.text.engine.DummyContentEngine` so every provider behaves
    identically above the word level.
    """

    @property
    def name(self) -> str: ...

    def word(self, rng: Random) -> str: ...


def letter_stream(rng: Random, length: int) -> str:
    """Build a pronounceable-but-nonsense word of exactly ``length`` characters."""
    if length <= 0:
        raise ValueError("word length must be positive")
    if length == 1:
        return rng.choice(CONSONANTS)
    out: list[str] = []
    vowel_next = rng.random() < 0.5
    for _ in range(length):
        out.append(rng.choice(VOWELS if vowel_next else CONSONANTS))
        vowel_next = not vowel_next
    return "".join(out)
