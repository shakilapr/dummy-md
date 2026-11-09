from __future__ import annotations

import hashlib

import pytest

import dummy_md
from dummy_md import DocumentSpec, ElementRule, Generator, LengthSpec
from dummy_md.core.budget import Unit, measure_text
from dummy_md.core.engine import SECTION_CHARS
from dummy_md.exceptions import BudgetError, ConfigurationError, DialectError
from dummy_md.renderers import get_renderer


def chars_of(text: str) -> int:
    return measure_text(text, "chars")


def test_generate_returns_markdown() -> None:
    text = dummy_md.generate(length=800, seed=7)
    assert text.endswith("\n")
    assert len(text) > 400
    assert dummy_md.validate(text).ok


def test_same_seed_is_byte_identical() -> None:
    first = dummy_md.generate(length=1500, seed=99)
    second = dummy_md.generate(length=1500, seed=99)
    assert (
        hashlib.sha256(first.encode()).hexdigest()
        == hashlib.sha256(second.encode()).hexdigest()
    )


def test_different_seeds_differ() -> None:
    assert dummy_md.generate(length=1200, seed=1) != dummy_md.generate(
        length=1200, seed=2
    )


def test_approximate_length_within_tolerance() -> None:
    for seed in range(5):
        text = dummy_md.generate(length=2000, seed=seed)
        assert abs(chars_of(text) - 2000) <= 100  # default tolerance is 5%


def test_exact_chars() -> None:
    text = dummy_md.generate(length=1234, mode="exact", seed=5)
    assert chars_of(text) == 1234


def test_exact_words() -> None:
    spec = DocumentSpec(
        seed=3, length=LengthSpec(value=120, unit="words", mode="exact")
    )
    generator = Generator(spec)
    generator.generate()
    document = generator.to_ast()
    from dummy_md.core.budget import count_words

    assert count_words(document) == 120


def test_zero_length_is_empty() -> None:
    assert dummy_md.generate(length=0) == ""


def test_small_documents_omit_frontmatter() -> None:
    text = dummy_md.generate(length=60, dialect="extended", seed=1)
    assert not text.startswith("---\n")
    assert not text.startswith("{\n")
    assert abs(chars_of(text) - 60) <= 3


def test_chunks_concatenate_to_generate() -> None:
    cases: tuple[tuple[Unit, int], ...] = (
        ("chars", 5000),
        ("words", 300),
        ("blocks", 20),
    )
    for unit, length in cases:
        whole = dummy_md.generate(length=length, unit=unit, seed=11)
        streamed = "".join(dummy_md.iter_chunks(length=length, unit=unit, seed=11))
        assert streamed == whole


def test_large_document_is_sectioned() -> None:
    length = SECTION_CHARS * 2 + 500
    chunks = list(dummy_md.iter_chunks(length=length, seed=2))
    assert len(chunks) > 1
    assert "".join(chunks) == dummy_md.generate(length=length, seed=2)


def test_to_ast_matches_rendered_output() -> None:
    spec = DocumentSpec(
        dialect="gfm",
        seed=21,
        length=LengthSpec(value=900),
    )
    generator = Generator(spec)
    text = generator.generate()
    document = generator.to_ast()
    renderer = get_renderer(generator.registry.dialect("gfm"))
    assert renderer.render(document) == text


def test_write_matches_generate(tmp_path: object) -> None:
    from pathlib import Path

    directory = Path(str(tmp_path))
    target = dummy_md.write(directory / "fixture.md", length=700, seed=4)
    assert target.read_text(encoding="utf-8") == dummy_md.generate(length=700, seed=4)


def test_min_count_is_respected() -> None:
    spec = DocumentSpec(
        seed=1,
        length=LengthSpec(value=12_000),
        elements={"table": ElementRule(min_count=3)},
    )
    document = Generator(spec).to_ast()
    from dummy_md.core.nodes import Table

    tables = [block for block in document.children if isinstance(block, Table)]
    assert len(tables) >= 3


def test_max_count_is_respected() -> None:
    spec = DocumentSpec(
        seed=1,
        length=LengthSpec(value=4000),
        elements={"thematic_break": ElementRule(max_count=1)},
    )
    document = Generator(spec).to_ast()
    from dummy_md.core.nodes import ThematicBreak

    rules = [block for block in document.children if isinstance(block, ThematicBreak)]
    assert len(rules) <= 1


def test_commonmark_output_has_no_tables() -> None:
    text = dummy_md.generate(length=3000, dialect="commonmark", seed=8)
    assert "|---" not in text.replace(" ", "")
    assert dummy_md.validate(text, "commonmark").ok


def test_dialect_gating_errors() -> None:
    with pytest.raises(DialectError):
        dummy_md.generate(length=100, dialect="commonmark", include=["table.pipe"])
    with pytest.raises(ConfigurationError):
        dummy_md.generate(length=100, include=["heading.nope"])
    with pytest.raises(DialectError):
        dummy_md.generate(length=100, dialect="nope")


def test_infeasible_exact_budget_raises() -> None:
    with pytest.raises(BudgetError) as excinfo:
        dummy_md.generate(
            length=1,
            mode="exact",
            seed=1,
            include=["table.pipe", "heading.atx.h1"],
            elements={"table": ElementRule(min_count=2)},
        )
    assert excinfo.value.requested == 1


def test_presets_are_selectable() -> None:
    assert "readme" in dummy_md.available_presets()
    text = dummy_md.generate(length=1500, preset="readme", seed=3)
    assert text.startswith("# ")
    assert dummy_md.validate(text).ok


def test_every_preset_generates_valid_small_documents() -> None:
    for name in dummy_md.available_presets():
        for seed in (1, 7):
            text = dummy_md.generate(length=1200, preset=name, seed=seed)
            assert text, f"{name} produced nothing"
            assert dummy_md.validate(text).ok, f"{name} invalid"


def test_advanced_spec_from_readme() -> None:
    from dummy_md.core.nodes import Heading, Table

    spec = DocumentSpec(
        dialect="gfm",
        seed=42,
        length=LengthSpec(value=8000, unit="chars", mode="approximate", tolerance=0.03),
        include=["heading.*", "paragraph.*", "table.*", "code.*", "list.*"],
        elements={
            "heading": ElementRule(min_count=3, max_count=10, weight=3),
            "paragraph": ElementRule(weight=10),
            "table": ElementRule(min_count=2, weight=4),
        },
        max_nesting_depth=3,
    )
    generator = Generator(spec)
    text = generator.generate()
    document = generator.to_ast()
    headings = [block for block in document.children if isinstance(block, Heading)]
    tables = [block for block in document.children if isinstance(block, Table)]
    assert 3 <= len(headings) <= 10
    assert len(tables) >= 2
    assert abs(chars_of(text) - 8000) <= 240


def test_unknown_preset_errors() -> None:
    with pytest.raises(ConfigurationError, match="preset"):
        dummy_md.generate(length=100, preset="nope")


def test_available_elements_filtered_by_dialect() -> None:
    gfm = set(dummy_md.available_elements("gfm"))
    commonmark = set(dummy_md.available_elements("commonmark"))
    assert "table.pipe" in gfm
    assert "table.pipe" not in commonmark
    assert commonmark < gfm


def test_text_style_changes_content() -> None:
    lorem = dummy_md.generate(length=600, text_style="lorem", seed=1)
    tokens = dummy_md.generate(length=600, text_style="tokens", seed=1)
    assert lorem != tokens
    assert any(word in lorem.lower() for word in ("lorem", "ipsum", "dolor", "amet"))


def test_max_nesting_depth_is_respected() -> None:
    text = dummy_md.generate(
        length=2500,
        seed=5,
        max_nesting_depth=1,
        include=["list.*", "paragraph.*"],
    )
    deepest = 0
    for line in text.split("\n"):
        if line.startswith("  ") and line.strip().startswith(("-", "1.")):
            deepest = max(deepest, 1)
    assert deepest == 0
