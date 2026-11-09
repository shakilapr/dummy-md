from __future__ import annotations

import re
from random import Random

import pytest

from dummy_md.text import TEXT_PROVIDERS, DummyContentEngine
from dummy_md.text.base import letter_stream
from dummy_md.text.lorem import LOREM
from dummy_md.text.pseudowords import PSEUDOWORDS
from dummy_md.text.tokens import ALPHANUMERIC, TOKENS


def engine(seed: int = 7, provider_name: str = "pseudowords") -> DummyContentEngine:
    return DummyContentEngine(Random(seed), TEXT_PROVIDERS[provider_name])


def test_provider_registry_names() -> None:
    assert set(TEXT_PROVIDERS) == {"pseudowords", "lorem", "tokens"}
    assert TEXT_PROVIDERS["lorem"].name == "lorem"


def test_same_seed_same_text() -> None:
    first = engine(11)
    second = engine(11)
    assert [first.paragraph() for _ in range(5)] == [
        second.paragraph() for _ in range(5)
    ]


def test_different_seeds_differ() -> None:
    assert engine(1).paragraph() != engine(2).paragraph()


def test_word_length_is_bounded() -> None:
    content = engine()
    for _ in range(200):
        word = content.word(min_length=3, max_length=9)
        assert 3 <= len(word) <= 9
        assert word.isalpha() and word.islower()


def test_word_of_length_is_exact() -> None:
    content = engine()
    for length in range(1, 30):
        word = content.word_of_length(length)
        assert len(word) == length
        assert word.isalpha()


def test_letter_stream_rejects_nonpositive() -> None:
    with pytest.raises(ValueError):
        letter_stream(Random(1), 0)


def test_sentence_shape() -> None:
    content = engine()
    for _ in range(100):
        sentence = content.sentence()
        assert sentence[0].isupper()
        assert sentence[-1] in ".?!"
        assert "\n" not in sentence


def test_paragraph_contains_multiple_sentences() -> None:
    paragraph = engine().paragraph(min_sentences=2, max_sentences=4)
    assert paragraph.count(".") + paragraph.count("?") + paragraph.count("!") >= 2


def test_heading_phrase_is_title_cased() -> None:
    phrase = engine().heading_phrase(level=1)
    assert phrase.split()[0][0].isupper()
    assert "\n" not in phrase


def test_identifier_styles() -> None:
    content = engine()
    assert re.fullmatch(r"[a-z]+_[a-z]+", content.identifier(style="snake_case"))
    assert re.fullmatch(r"[a-z]+-[a-z]+", content.identifier(style="kebab-case"))
    assert re.fullmatch(r"[a-z]+[A-Z][a-z]+", content.identifier(style="camelCase"))
    assert re.fullmatch(
        r"[A-Z][a-z]+[A-Z][a-z]+", content.identifier(style="PascalCase")
    )
    assert re.fullmatch(r"[A-Z]+_[A-Z]+", content.identifier(style="CONSTANT_CASE"))


def test_url_and_path_are_plausible() -> None:
    content = engine()
    url = content.url()
    assert url.startswith("https://")
    assert " " not in url
    path = content.path()
    assert path.endswith(".md")
    assert " " not in path


def test_email_shape() -> None:
    email = engine().email()
    assert re.fullmatch(r"[a-z.-]+@[a-z.-]+\.[a-z]+", email)


def test_lorem_uses_latin_words() -> None:
    text = engine(3, "lorem").paragraph()
    assert any(word in text.lower() for word in LOREM._words[:10])


def test_token_provider_produces_unpronounceable_clusters() -> None:
    word = TOKENS.word(Random(5))
    assert 3 <= len(word) <= 9
    assert word.isalpha()


def test_alphanumeric_provider_shape() -> None:
    assert re.fullmatch(r"[a-z]{2}\d{2}", ALPHANUMERIC.word(Random(1)))


def test_pseudoword_avoids_triple_letters() -> None:
    rng = Random(9)
    for _ in range(300):
        word = PSEUDOWORDS.word(rng)
        assert not re.search(r"(.)\1\1", word)


def test_numeric_cells_follow_ratio() -> None:
    content = engine(4)
    cells = [content.table_cell(numeric_ratio=1.0) for _ in range(20)]
    assert all(cell.isdigit() for cell in cells)
    prose = [content.table_cell(numeric_ratio=0.0) for _ in range(20)]
    assert all(not cell.isdigit() for cell in prose)


def test_date_is_deterministic_shape() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", engine().date())
