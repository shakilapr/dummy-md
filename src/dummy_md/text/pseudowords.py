"""Syllable-based artificial words: the default placeholder style."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

ONSETS: tuple[str, ...] = (
    "b",
    "c",
    "d",
    "f",
    "g",
    "h",
    "j",
    "k",
    "l",
    "m",
    "n",
    "p",
    "r",
    "s",
    "t",
    "v",
    "w",
    "z",
    "br",
    "ch",
    "cl",
    "cr",
    "dr",
    "fl",
    "fr",
    "gl",
    "gr",
    "pl",
    "pr",
    "sh",
    "sl",
    "st",
    "th",
    "tr",
)
NUCLEI: tuple[str, ...] = (
    "a",
    "e",
    "i",
    "o",
    "u",
    "ai",
    "au",
    "ea",
    "ee",
    "ie",
    "oa",
    "oo",
    "ou",
    "y",
)
CODAS: tuple[str, ...] = (
    "",
    "n",
    "r",
    "s",
    "l",
    "m",
    "t",
    "ck",
    "nd",
    "nt",
    "st",
    "sh",
    "th",
    "ll",
    "ss",
    "x",
)


@dataclass(frozen=True, slots=True)
class PseudowordProvider:
    """Pronounceable invented words built from onset/nucleus/coda tables."""

    name: str = "pseudowords"
    max_syllables: int = 3
    _onsets: tuple[str, ...] = field(default=ONSETS, repr=False)
    _nuclei: tuple[str, ...] = field(default=NUCLEI, repr=False)
    _codas: tuple[str, ...] = field(default=CODAS, repr=False)

    def word(self, rng: Random) -> str:
        syllables = rng.randint(1, self.max_syllables)
        parts: list[str] = []
        for index in range(syllables):
            onset = rng.choice(self._onsets)
            nucleus = rng.choice(self._nuclei)
            coda = rng.choice(self._codas) if index == syllables - 1 else ""
            parts.append(f"{onset}{nucleus}{coda}")
        return _collapse_triples("".join(parts))


def _collapse_triples(word: str) -> str:
    """Remove a third repeated letter so words stay pronounceable."""
    kept: list[str] = [word[0]]
    for character in word[1:]:
        if len(kept) >= 2 and kept[-1] == kept[-2] == character:
            continue
        kept.append(character)
    return "".join(kept)


PSEUDOWORDS = PseudowordProvider()
