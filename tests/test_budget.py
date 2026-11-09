from __future__ import annotations

import random

import pytest

from dummy_md.core.budget import (
    BudgetTracker,
    count_blocks,
    count_words,
    measure,
    measure_text,
)
from dummy_md.core.context import GenerationContext, HeadingTracker, ReferenceRegistry
from dummy_md.core.dialects import get_dialect
from dummy_md.core.nodes import (
    Document,
    FootnoteDefinition,
    LinkDefinition,
    Paragraph,
    Text,
)
from dummy_md.exceptions import BudgetError
from dummy_md.text import DummyContentEngine


def tracker(**kwargs: object) -> BudgetTracker:
    defaults: dict[str, object] = {"unit": "chars", "target": 100}
    defaults.update(kwargs)
    return BudgetTracker(**defaults)  # type: ignore[arg-type]


def test_measure_text_units() -> None:
    text = "alpha beta\nsecond line\n"
    assert measure_text(text, "chars") == len(text) - 1
    assert measure_text(text, "lines") == 2
    assert measure_text("", "lines") == 0
    assert measure_text("abc", "bytes") == 3
    assert measure_text("é", "bytes") == 2


def test_measure_rejects_structural_unit_in_text() -> None:
    with pytest.raises(ValueError, match="not a serialized unit"):
        measure_text("abc", "words")


def test_count_words_and_blocks() -> None:
    document = Document(
        children=(
            Paragraph(children=(Text("one two three"),)),
            Paragraph(children=(Text("four"),)),
        )
    )
    assert count_words(document) == 4
    assert count_blocks(document) == 2
    assert measure(document, "ignored", "words") == 4
    assert measure(document, "ignored", "blocks") == 2


def test_tracker_records_and_reports_delta() -> None:
    budget = tracker(target=100)
    assert budget.remaining == 100
    budget.record(40)
    assert budget.remaining == 60
    assert budget.delta(55) == 45


def test_tracker_accepts_within_tolerance() -> None:
    approximate = tracker(target=1000, tolerance=0.05)
    assert approximate.accepts(1050)
    assert approximate.accepts(950)
    assert not approximate.accepts(1051)


def test_exact_mode_requires_exact_value() -> None:
    exact = tracker(target=100, mode="exact")
    assert exact.accepts(100)
    assert not exact.accepts(99)
    with pytest.raises(BudgetError) as excinfo:
        exact.enforce(99)
    assert excinfo.value.requested == 100
    assert excinfo.value.achievable == 99


def test_tracker_validates_inputs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        tracker(target=-1)
    with pytest.raises(ValueError, match="unknown unit"):
        tracker(unit="pages")
    with pytest.raises(ValueError, match="unknown mode"):
        tracker(mode="fast")
    with pytest.raises(ValueError, match="tolerance"):
        tracker(tolerance=2)


def test_heading_tracker_clamps_progression() -> None:
    headings = HeadingTracker()
    assert headings.next_level(3) == 3
    headings.record(3)
    assert headings.next_level(6) == 4
    assert headings.next_level(6, allow_skips=True) == 6
    headings.reset()
    assert headings.next_level(1) == 1


def test_reference_registry_dedupes_and_counts() -> None:
    refs = ReferenceRegistry()
    first = refs.add_link(LinkDefinition(label="a", destination="/a"))
    again = refs.add_link(LinkDefinition(label="a", destination="/b"))
    assert first is again
    definition = FootnoteDefinition(label="1", children=())
    refs.add_footnote(definition)
    refs.add_footnote(definition)
    assert len(refs.footnotes) == 1
    assert (refs.link_label(), refs.link_label()) == ("ref-1", "ref-2")
    assert (refs.footnote_label(), refs.footnote_label()) == ("1", "2")


def test_context_nested_shares_state() -> None:
    context = GenerationContext(
        rng=random.Random(1),
        dialect=get_dialect("gfm"),
        text=DummyContentEngine(random.Random(1)),
        active_features=frozenset({"heading.atx.h1"}),
        budget=tracker(),
        max_depth=2,
    )
    assert context.supports("heading.atx.h1")
    assert not context.supports("table.pipe")
    assert context.active_in_family("heading") == ("heading.atx.h1",)
    child = context.nested()
    assert child.depth == 1
    assert child.rng is context.rng
    assert context.can_nest
    assert not child.nested().can_nest
