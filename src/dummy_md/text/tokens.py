"""Random token and alphanumeric providers for parser stress fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from dummy_md.text.base import CONSONANTS, VOWELS, letter_stream


@dataclass(frozen=True, slots=True)
class TokenProvider:
    """Unpronounceable ASCII clusters, useful for stressing tokenizers."""

    name: str = "tokens"
    min_length: int = 3
    max_length: int = 9
    vowel_ratio: float = 0.2

    def word(self, rng: Random) -> str:
        length = rng.randint(self.min_length, self.max_length)
        letters: list[str] = []
        for _ in range(length):
            pool = VOWELS if rng.random() < self.vowel_ratio else CONSONANTS
            letters.append(rng.choice(pool))
        return "".join(letters)


@dataclass(frozen=True, slots=True)
class AlphanumericProvider:
    """Mixed letter/digit tokens such as ``ax19`` or ``bz04``."""

    name: str = "alphanumeric"

    def word(self, rng: Random) -> str:
        letters = "".join(rng.choice(CONSONANTS) for _ in range(2))
        digits = "".join(str(rng.randrange(10)) for _ in range(2))
        return letters + digits


@dataclass(frozen=True, slots=True)
class FillerProvider:
    """Words of an exact requested length, used to close a length delta."""

    name: str = "filler"

    def word(self, rng: Random) -> str:
        return letter_stream(rng, rng.randint(2, 10))


TOKENS = TokenProvider()
ALPHANUMERIC = AlphanumericProvider()
FILLER = FillerProvider()
