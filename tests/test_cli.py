from __future__ import annotations

from pathlib import Path

import pytest

import dummy_md
from dummy_md.cli import build_parser, main, parse_size


def test_generate_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["generate", "--chars", "400", "--seed", "3"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("# ")
    assert len(captured.out) >= 300


def test_generate_matches_api(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    target = tmp_path / "fixture.md"
    exit_code = main(
        [
            "generate",
            "--words",
            "150",
            "--seed",
            "9",
            "--output",
            str(target),
        ]
    )
    assert exit_code == 0
    expected = dummy_md.generate(length=150, unit="words", seed=9)
    assert target.read_text(encoding="utf-8") == expected


def test_generate_size_bytes(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["generate", "--bytes", "2KB", "--seed", "1"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert 1900 <= len(captured.out.encode("utf-8")) <= 2100


def test_invalid_feature_pattern_reports_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["generate", "--chars", "100", "--include", "nope.*"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "dummy-md: error:" in captured.err


def test_unknown_dialect_reports_error(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["generate", "--chars", "100", "--dialect", "markdown"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "unknown dialect" in captured.err


def test_elements_lists_implemented(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["elements", "--dialect", "commonmark"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "heading.atx.h1" in captured.out.split()
    assert "table.pipe" not in captured.out.split()


def test_elements_all_marks_planned(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["elements", "--all"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "table.grid  (planned)" in captured.out


def test_dialects_and_presets(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["dialects"]) == 0
    assert main(["presets"]) == 0
    captured = capsys.readouterr()
    assert "gfm" in captured.out
    assert "readme" in captured.out


def test_validate_good_and_bad_files(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    good = tmp_path / "good.md"
    good.write_text(dummy_md.generate(length=400, seed=1), encoding="utf-8")
    assert main(["validate", str(good)]) == 0
    assert "ok" in capsys.readouterr().out

    bad = tmp_path / "bad.md"
    bad.write_text("```\nunclosed fence\n", encoding="utf-8")
    assert main(["validate", str(bad)]) == 1
    assert "unbalanced" in capsys.readouterr().err


def test_missing_file_reports_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", "does-not-exist.md"]) == 1
    assert "error" in capsys.readouterr().err


def test_size_parsing() -> None:
    assert parse_size("500") == 500
    assert parse_size("50KB") == 50_000
    assert parse_size("1.5 MB") == 1_500_000


def test_size_parsing_rejects_garbage() -> None:
    from dummy_md.exceptions import DummyMdError

    with pytest.raises(DummyMdError):
        parse_size("many")


def test_parser_requires_subcommand() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
