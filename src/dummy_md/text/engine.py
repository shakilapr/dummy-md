"""Context-aware placeholder content used by every element generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Literal

from dummy_md.text.base import TextProvider, letter_stream
from dummy_md.text.pseudowords import PSEUDOWORDS

IdentifierStyle = Literal[
    "snake_case", "kebab-case", "camelCase", "PascalCase", "CONSTANT_CASE"
]
_SENTENCE_ENDINGS: tuple[str, ...] = (".", ".", ".", ".", ".", ".", ".", ".", "?", "!")
_COMMAS = (",",)
_TLDS: tuple[str, ...] = ("com", "org", "net", "io", "dev")
_DOMAINS: tuple[str, ...] = ("example.com", "example.org", "example.net")


@dataclass(slots=True)
class DummyContentEngine:
    """Semantic text requests: headings, sentences, cells, identifiers, URLs.

    Every method draws exclusively from ``rng`` so two engines with the same
    seeded RNG and provider produce identical output.
    """

    rng: Random
    provider: TextProvider = field(default=PSEUDOWORDS)

    # -- words ------------------------------------------------------------
    def word(self, *, min_length: int = 2, max_length: int = 14) -> str:
        if min_length < 1 or max_length < min_length:
            raise ValueError("invalid word length bounds")
        for _ in range(8):
            candidate = self.provider.word(self.rng)
            if min_length <= len(candidate) <= max_length:
                return candidate
        return letter_stream(self.rng, min(max_length, max(min_length, 4)))

    def word_of_length(self, length: int) -> str:
        """A word of exactly ``length`` lowercase letters."""
        return letter_stream(self.rng, length)

    def words(self, count: int) -> list[str]:
        return [self.word() for _ in range(count)]

    def token(self) -> str:
        letters = "".join(letter_stream(self.rng, 3))
        return f"{letters}{self.number(10, 99)}"

    # -- prose ------------------------------------------------------------
    def phrase(
        self, *, min_words: int = 1, max_words: int = 4, title_case: bool = False
    ) -> str:
        count = self.rng.randint(min_words, max_words)
        words = self.words(count)
        if title_case:
            words = [w.capitalize() for w in words]
        return " ".join(words)

    def heading_phrase(self, level: int = 2) -> str:
        if level == 1:
            return self.phrase(min_words=2, max_words=5, title_case=True)
        return self.phrase(min_words=1, max_words=6, title_case=True)

    def sentence(self, *, min_words: int = 5, max_words: int = 14) -> str:
        count = self.rng.randint(min_words, max_words)
        words = self.words(count)
        words[0] = words[0].capitalize()
        if count > 5 and self.rng.random() < 0.35:
            position = self.rng.randint(2, count - 3)
            words[position] = words[position] + _COMMAS[0]
        return " ".join(words) + self.rng.choice(_SENTENCE_ENDINGS)

    def paragraph(self, *, min_sentences: int = 2, max_sentences: int = 5) -> str:
        count = self.rng.randint(min_sentences, max_sentences)
        return " ".join(self.sentence() for _ in range(count))

    # -- structured data --------------------------------------------------
    def table_cell(self, *, numeric_ratio: float = 0.3) -> str:
        roll = self.rng.random()
        if roll < numeric_ratio:
            return str(self.number(0, 9999))
        if roll < numeric_ratio + 0.15:
            return self.decimal(places=2)
        return self.phrase(min_words=1, max_words=3)

    def number(self, minimum: int = 0, maximum: int = 9999) -> int:
        return self.rng.randint(minimum, maximum)

    def decimal(self, *, places: int = 2) -> str:
        whole = self.number(0, 999)
        fraction = "".join(str(self.rng.randrange(10)) for _ in range(places))
        return f"{whole}.{fraction}"

    def date(self) -> str:
        year = self.number(2015, 2030)
        month = self.number(1, 12)
        day = self.number(1, 28)
        return f"{year:04d}-{month:02d}-{day:02d}"

    def choice(self, options: tuple[str, ...]) -> str:
        if not options:
            raise ValueError("cannot choose from an empty sequence")
        return self.rng.choice(options)

    # -- identifiers and destinations -------------------------------------
    def identifier(
        self, *, style: IdentifierStyle = "snake_case", word_count: int = 2
    ) -> str:
        words = self.words(word_count)
        if style == "snake_case":
            return "_".join(words)
        if style == "kebab-case":
            return "-".join(words)
        if style == "camelCase":
            head, *tail = words
            return head + "".join(w.capitalize() for w in tail)
        if style == "PascalCase":
            return "".join(w.capitalize() for w in words)
        return "_".join(w.upper() for w in words)

    def slug(self) -> str:
        return "-".join(self.words(self.rng.randint(1, 3)))

    def url(self, *, secure: bool = True) -> str:
        scheme = "https" if secure else "http"
        domain = self.rng.choice(_DOMAINS)
        depth = self.rng.randint(0, 2)
        if depth == 0:
            return f"{scheme}://{domain}/{self.slug()}"
        segments = "/".join(self.slug() for _ in range(depth + 1))
        return f"{scheme}://{domain}/{segments}"

    def path(self, *, extension: str = ".md") -> str:
        depth = self.rng.randint(0, 2)
        segments = "/".join(self.slug() for _ in range(depth))
        filename = self.slug() + extension
        return f"{segments}/{filename}" if segments else filename

    def email(self) -> str:
        local = f"{self.slug()}.{self.word()}"
        return f"{local}@{self.slug()}.{self.rng.choice(_TLDS)}"

    def label(self) -> str:
        """A short human-readable label, e.g. for a link text or alt text."""
        return self.phrase(min_words=1, max_words=3, title_case=True)
