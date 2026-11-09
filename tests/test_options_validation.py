"""Option validation: invalid knobs must fail loudly, not emit broken Markdown."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from dummy_md.elements import (
    CodeOptions,
    DiagramOptions,
    FootnoteOptions,
    FrontMatterOptions,
    HeadingOptions,
    ImageOptions,
    LinkOptions,
    ListOptions,
    MathOptions,
    ParagraphOptions,
    QuoteOptions,
    TableOptions,
    ThematicBreakOptions,
    build_options,
)
from dummy_md.exceptions import ConfigurationError


@pytest.mark.parametrize(
    "factory",
    [
        lambda: TableOptions(min_columns=0),
        lambda: TableOptions(min_rows=3, max_rows=2),
        lambda: TableOptions(min_cell_words=0),
        lambda: TableOptions(numeric_ratio=1.5),
        lambda: TableOptions(style_ratio=-0.1),
        lambda: ListOptions(min_items=0),
        lambda: ListOptions(min_items=3, max_items=2),
        lambda: ListOptions(max_depth=0),
        lambda: ListOptions(task_ratio=2.0),
        lambda: ParagraphOptions(min_sentences=0),
        lambda: ParagraphOptions(min_sentences=3, max_sentences=2),
        lambda: ParagraphOptions(sentence_min_words=9, sentence_max_words=4),
        lambda: ParagraphOptions(inline_ratio=2.0),
        lambda: CodeOptions(info_ratio=-0.1),
        lambda: ImageOptions(figure_ratio=2.0),
        lambda: QuoteOptions(lazy_ratio=-1.0),
        lambda: FootnoteOptions(multiline_ratio=2.0),
        lambda: MathOptions(delimiter="foo"),  # type: ignore[arg-type]
        lambda: MathOptions(label_ratio=2.0),
        lambda: DiagramOptions(fence_info=""),
        lambda: FrontMatterOptions(max_fields=0),
        lambda: HeadingOptions(levels=()),
        lambda: HeadingOptions(levels=(0, 2)),
        lambda: LinkOptions(min_links=0),
        lambda: LinkOptions(min_links=3, max_links=2),
        lambda: ThematicBreakOptions(spacings=()),
        lambda: ThematicBreakOptions(spacings=(-1,)),
    ],
)
def test_invalid_options_raise(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        factory()


def test_ratio_boundaries_are_valid() -> None:
    assert TableOptions(numeric_ratio=0.0, empty_ratio=1.0).numeric_ratio == 0.0
    assert ParagraphOptions(inline_ratio=1.0).inline_ratio == 1.0
    assert ListOptions(nested_ratio=0.0).nested_ratio == 0.0


def test_mapping_options_report_configuration_errors() -> None:
    with pytest.raises(ConfigurationError, match="invalid options"):
        build_options(TableOptions, {"min_columns": 0}, "table")
    with pytest.raises(ConfigurationError, match="invalid options"):
        build_options(MathOptions, {"delimiter": "nope"}, "math")
