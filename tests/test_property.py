from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from markdown_it import MarkdownIt

import dummy_md
from dummy_md.core.budget import measure_text

DIALECTS = st.sampled_from(["commonmark", "gfm", "extended"])
UNITS = st.sampled_from(["chars", "words", "blocks"])
TEXT_STYLES = st.sampled_from(["pseudowords", "lorem", "tokens"])

PARSER = MarkdownIt("commonmark").enable("table")


@settings(max_examples=12, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=10_000),
    dialect=DIALECTS,
    unit=UNITS,
    style=TEXT_STYLES,
    length=st.integers(min_value=50, max_value=1500),
)
def test_generation_never_crashes_and_parses(
    seed: int, dialect: str, unit: str, style: str, length: int
) -> None:
    text = dummy_md.generate(
        length=length,
        unit=unit,  # type: ignore[arg-type]
        dialect=dialect,
        seed=seed,
        text_style=style,
    )
    assert text
    PARSER.parse(text)
    assert dummy_md.validate(text, dialect).ok


@settings(max_examples=10, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=5_000),
    target=st.integers(min_value=200, max_value=4000),
)
def test_approximate_length_tolerance(seed: int, target: int) -> None:
    text = dummy_md.generate(length=target, seed=seed, mode="approximate")
    actual = measure_text(text, "chars")
    assert abs(actual - target) <= 0.05 * target


@settings(max_examples=8, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2_000),
    target=st.integers(min_value=100, max_value=2500),
)
def test_exact_char_target_is_hit(seed: int, target: int) -> None:
    text = dummy_md.generate(length=target, seed=seed, mode="exact")
    assert measure_text(text, "chars") == target
