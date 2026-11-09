from __future__ import annotations

import hashlib
import os
import subprocess
import sys

import pytest

import dummy_md
from dummy_md import DocumentSpec, Generator, LengthSpec


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_repeated_runs_match() -> None:
    first = dummy_md.generate(length=2500, seed=1234)
    second = dummy_md.generate(length=2500, seed=1234)
    assert digest(first) == digest(second)


def test_spec_is_reusable() -> None:
    spec = DocumentSpec(seed=77, length=LengthSpec(value=1500), dialect="extended")
    first = Generator(spec).generate()
    second = Generator(spec).generate()
    assert first == second


def test_different_dialects_differ() -> None:
    gfm = dummy_md.generate(length=1200, dialect="gfm", seed=5)
    extended = dummy_md.generate(length=1200, dialect="extended", seed=5)
    assert gfm != extended


def test_text_styles_are_deterministic() -> None:
    for style in ("pseudowords", "lorem", "tokens"):
        first = dummy_md.generate(length=800, seed=9, text_style=style)
        second = dummy_md.generate(length=800, seed=9, text_style=style)
        assert first == second


def _digest_in_subprocess(hash_seed: str) -> str:
    code = (
        "import hashlib, dummy_md; "
        "print(hashlib.sha256(dummy_md.generate(length=2000, seed=4242)"
        ".encode()).hexdigest())"
    )
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = hash_seed
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    return result.stdout.strip()


@pytest.mark.slow
def test_hash_seed_does_not_affect_output() -> None:
    assert _digest_in_subprocess("0") == _digest_in_subprocess("123456")


def test_same_seed_same_ast() -> None:
    spec = DocumentSpec(seed=31, length=LengthSpec(value=900))
    first = Generator(spec).to_ast()
    second = Generator(spec).to_ast()
    assert first == second
