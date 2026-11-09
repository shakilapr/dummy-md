"""Length units, measurement, and the budget ledger."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dummy_md.core.nodes import Document, Text, walk
from dummy_md.exceptions import BudgetError

Unit = Literal["chars", "words", "lines", "blocks", "bytes"]
Mode = Literal["approximate", "exact"]

UNITS: tuple[str, ...] = ("chars", "words", "lines", "blocks", "bytes")


def measure_text(text: str, unit: Unit) -> int:
    """Measure already-serialized output.

    ``chars`` excludes the trailing newline every renderer emits, so the count
    matches what a user sees in an editor's character counter.
    """
    if unit == "chars":
        return len(text[:-1]) if text.endswith("\n") else len(text)
    if unit == "lines":
        if not text:
            return 0
        return text.count("\n") + (0 if text.endswith("\n") else 1)
    if unit == "bytes":
        return len(text.encode("utf-8"))
    raise ValueError(f"unit {unit!r} is not a serialized unit")


def count_words(document: Document) -> int:
    words = 0
    for node in walk(document):
        if isinstance(node, Text):
            words += len(node.content.split())
    return words


def count_blocks(document: Document) -> int:
    return len(document.children)


def measure(document: Document, text: str, unit: Unit) -> int:
    if unit == "words":
        return count_words(document)
    if unit == "blocks":
        return count_blocks(document)
    return measure_text(text, unit)


@dataclass(slots=True)
class BudgetTracker:
    """Running ledger for the active unit."""

    unit: Unit
    target: int
    mode: Mode = "approximate"
    tolerance: float = 0.05
    consumed: int = 0

    def __post_init__(self) -> None:
        if self.target < 0:
            raise ValueError("budget target must be non-negative")
        if self.unit not in UNITS:
            raise ValueError(f"unknown unit {self.unit!r}")
        if self.mode not in {"approximate", "exact"}:
            raise ValueError(f"unknown mode {self.mode!r}")
        if not 0 <= self.tolerance <= 1:
            raise ValueError("tolerance must be between 0 and 1")

    @property
    def remaining(self) -> int:
        return self.target - self.consumed

    def record(self, amount: int) -> None:
        self.consumed += amount

    def delta(self, actual: int) -> int:
        return self.target - actual

    def accepts(self, actual: int) -> bool:
        if self.mode == "exact":
            return actual == self.target
        if self.target == 0:
            return actual == 0
        return abs(actual - self.target) <= self.tolerance * self.target

    def enforce(self, actual: int, *, operation: str = "document") -> None:
        if self.accepts(actual):
            return
        raise BudgetError(
            f"{self.unit} target not reached by {operation}",
            requested=self.target,
            achievable=actual,
        )
