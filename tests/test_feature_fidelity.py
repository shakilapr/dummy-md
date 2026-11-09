"""Fidelity tests: an implemented feature must reach the rendered output.

These tests exist because the catalog promises that ``implemented`` means the
engine can emit the construct. Several features were previously declared
implemented while no generator path produced them; each test here pins one of
those down.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import dummy_md
from dummy_md import DocumentSpec, ElementRule, Generator, LengthSpec
from dummy_md.core.catalog import IMPLEMENTED_IDS
from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    Blockquote,
    CodeBlock,
    InlineFootnote,
    ListBlock,
    Math,
    Paragraph,
    Table,
)
from dummy_md.elements import (
    FootnoteOptions,
    HeadingOptions,
    ListOptions,
    ParagraphOptions,
    QuoteOptions,
    TableOptions,
)
from dummy_md.exceptions import DialectError
from dummy_md.renderers import get_renderer
from tests.helpers import REGISTRY, build_context, document_of


def render_block(block: object, context: object) -> str:
    return get_renderer(context.dialect).render(  # type: ignore[attr-defined]
        document_of(block)  # type: ignore[arg-type]
    )


# -- inline math -------------------------------------------------------------
@pytest.mark.parametrize(
    ("feature", "delimiter", "marker"),
    [
        ("math.inline.dollar", "dollar", "$"),
        ("math.inline.paren", "bracket", "\\("),
    ],
)
def test_inline_math_reaches_output(feature: str, delimiter: str, marker: str) -> None:
    context = build_context(
        dialect="extended",
        include=(feature,),
        options={
            "paragraph": ElementRule(
                options=ParagraphOptions(
                    min_sentences=2,
                    max_sentences=2,
                    inline_ratio=1.0,
                    emoji_ratio=0.0,
                )
            )
        },
    )
    block = REGISTRY.generator("paragraph").generate(context)
    assert isinstance(block, Paragraph)
    maths = [node for node in block.children if isinstance(node, Math)]
    assert maths, "paragraph dropped the inline math decoration"
    assert maths[0].delimiter == delimiter
    assert marker in render_block(block, context)


def test_inline_math_guard_matches_the_delimiter() -> None:
    from dummy_md.core.dialects import get_dialect

    renderer = get_renderer(get_dialect("commonmark"))
    for delimiter in ("dollar", "bracket"):
        with pytest.raises(DialectError, match="inline math"):
            renderer.render(
                document_of(Paragraph(children=(Math("x", delimiter=delimiter),)))
            )


# -- inline footnote ---------------------------------------------------------
def test_inline_footnote_reaches_output() -> None:
    context = build_context(
        dialect="extended",
        include=("footnote.inline",),
        options={
            "paragraph": ElementRule(
                options=ParagraphOptions(
                    min_sentences=2,
                    max_sentences=2,
                    inline_ratio=1.0,
                    emoji_ratio=0.0,
                )
            )
        },
    )
    block = REGISTRY.generator("paragraph").generate(context)
    assert isinstance(block, Paragraph)
    assert any(isinstance(node, InlineFootnote) for node in block.children)
    assert "^[" in render_block(block, context)


# -- nested code / lists -----------------------------------------------------
def test_code_in_blockquote_is_nested() -> None:
    context = build_context(
        dialect="gfm",
        include=("code.in_blockquote",),
        options={
            "blockquote": ElementRule(options=QuoteOptions(extra_block_ratio=1.0))
        },
        seed=3,
    )
    block = REGISTRY.generator("blockquote").generate(context)
    assert isinstance(block, Blockquote)
    assert any(isinstance(child, CodeBlock) for child in block.children)


def test_code_in_list_is_nested() -> None:
    context = build_context(
        dialect="gfm",
        include=("code.in_list",),
        options={"list": ElementRule(options=ListOptions(extra_block_ratio=1.0))},
        seed=3,
    )
    block = REGISTRY.generator("list").generate(context)
    assert isinstance(block, ListBlock)
    assert any(
        isinstance(child, CodeBlock) for item in block.items for child in item.children
    )


def test_list_in_blockquote_is_nested() -> None:
    context = build_context(
        dialect="gfm",
        include=("list.in_blockquote",),
        options={
            "blockquote": ElementRule(options=QuoteOptions(extra_block_ratio=1.0))
        },
        seed=3,
    )
    block = REGISTRY.generator("blockquote").generate(context)
    assert isinstance(block, Blockquote)
    assert any(isinstance(child, ListBlock) for child in block.children)


# -- lazy continuation -------------------------------------------------------
def test_lazy_blockquote_renders_unprefixed_continuation() -> None:
    context = build_context(
        dialect="commonmark",
        include=("blockquote.lazy",),
        options={"blockquote": ElementRule(options=QuoteOptions(lazy_ratio=1.0))},
        seed=5,
    )
    block = REGISTRY.generator("blockquote").generate(context)
    assert isinstance(block, Blockquote)
    assert block.lazy
    text = render_block(block, context)
    lines = text.splitlines()
    assert lines[0].startswith("> ")
    assert len(lines) > 1
    assert not lines[1].startswith(">")


def test_blockquote_default_is_not_lazy() -> None:
    block = REGISTRY.generator("blockquote").generate(
        build_context(dialect="commonmark", include=("blockquote.single",))
    )
    assert isinstance(block, Blockquote)
    assert not block.lazy


def test_emoji_is_emitted_when_selected_alone() -> None:
    context = build_context(
        dialect="commonmark",
        include=("inline.emoji.unicode",),
        options={
            "paragraph": ElementRule(
                options=ParagraphOptions(emoji_ratio=1.0, inline_ratio=0.0)
            )
        },
    )
    block = REGISTRY.generator("paragraph").generate(context)
    assert "\U0001f642" in render_block(block, context)


@pytest.mark.parametrize(
    "feature", ["blockquote.heading", "blockquote.list", "blockquote.code"]
)
def test_single_extra_block_feature_is_emitted(feature: str) -> None:
    context = build_context(
        dialect="commonmark",
        include=(feature,),
        options={
            "blockquote": ElementRule(options=QuoteOptions(extra_block_ratio=1.0))
        },
        seed=11,
    )
    block = REGISTRY.generator("blockquote").generate(context)
    assert isinstance(block, Blockquote)
    assert len(block.children) >= 2, f"{feature} was dropped"


# -- heading levels ----------------------------------------------------------
def test_skipped_heading_level_requires_the_feature() -> None:
    options = {"heading": ElementRule(options=HeadingOptions(levels=(4,)))}
    allowed = build_context(
        dialect="gfm",
        include=("heading.atx.h1", "heading.atx.h4", "heading.levels.skipped"),
        options=options,
        seed=2,
    )
    allowed.headings.record(1)
    assert REGISTRY.generator("heading").generate(allowed).level == 4  # type: ignore[attr-defined]

    clamped = build_context(
        dialect="gfm",
        include=("heading.atx.h1", "heading.atx.h4"),
        options=options,
        seed=2,
    )
    clamped.headings.record(1)
    assert REGISTRY.generator("heading").generate(clamped).level == 2  # type: ignore[attr-defined]


# -- tables ------------------------------------------------------------------
def test_escaped_pipe_in_cells() -> None:
    context = build_context(
        dialect="gfm",
        include=("table.pipe", "table.cell.escaped_pipe"),
        options={
            "table": ElementRule(
                options=TableOptions(
                    min_rows=2,
                    max_rows=2,
                    min_columns=2,
                    max_columns=2,
                    min_cell_words=2,
                    max_cell_words=2,
                    inline_ratio=1.0,
                    empty_ratio=0.0,
                )
            )
        },
        seed=7,
    )
    block = REGISTRY.generator("table").generate(context)
    assert isinstance(block, Table)
    text = render_block(block, context)
    assert "\\|" in text


def test_many_columns_feature_widens_tables() -> None:
    context = build_context(
        dialect="gfm",
        include=("table.pipe", "table.columns.many"),
        options={
            "table": ElementRule(
                options=TableOptions(
                    min_columns=2,
                    max_columns=4,
                    min_rows=1,
                    max_rows=1,
                    many_ratio=1.0,
                )
            )
        },
        seed=4,
    )
    block = REGISTRY.generator("table").generate(context)
    assert isinstance(block, Table)
    assert len(block.header) >= 6


def test_numeric_payload_feature_controls_cells() -> None:
    numeric = build_context(
        dialect="gfm",
        include=("table.pipe", "table.payload.numeric"),
        options={
            "table": ElementRule(
                options=TableOptions(
                    min_rows=2,
                    max_rows=2,
                    min_cell_words=1,
                    max_cell_words=1,
                    numeric_ratio=1.0,
                    empty_ratio=0.0,
                    inline_ratio=0.0,
                )
            )
        },
        seed=6,
    )
    block = REGISTRY.generator("table").generate(numeric)
    assert isinstance(block, Table)
    cells = [cell for row in block.rows for cell in row]
    text = render_block(block, numeric)
    numerals = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    assert cells and numerals, "numeric payload did not produce numeric cells"

    plain = build_context(
        dialect="gfm",
        include=("table.pipe",),
        options={
            "table": ElementRule(
                options=TableOptions(
                    min_rows=2,
                    max_rows=2,
                    numeric_ratio=1.0,
                    empty_ratio=0.0,
                    inline_ratio=0.0,
                )
            )
        },
        seed=6,
    )
    plain_block = REGISTRY.generator("table").generate(plain)
    plain_text = render_block(plain_block, plain)
    assert not re.search(r"\b\d+(?:\.\d+)?\b", plain_text), (
        "numeric cells leaked without table.payload.numeric"
    )


# -- footnote options --------------------------------------------------------
def test_footnote_multiline_option_is_used() -> None:
    context = build_context(
        dialect="extended",
        include=("footnote.reference", "footnote.multiline"),
        options={"footnote": ElementRule(options=FootnoteOptions(multiline_ratio=1.0))},
        seed=2,
    )
    REGISTRY.generator("footnote").generate(context)
    definition = context.refs.footnotes["1"]
    assert len(definition.children) == 2


# -- static wiring guard -----------------------------------------------------
_BASE_CASES: frozenset[str] = frozenset(
    {
        "doc.body",
        "heading.atx.h1",
        "heading.atx.h2",
        "heading.atx.h3",
        "heading.atx.h4",
        "heading.atx.h5",
        "heading.atx.h6",
        "heading.setext.h1",
        "heading.setext.h2",
        "heading.sequence",
        "paragraph.single_line",
        "blockquote.single",
        "image.alt",
        "image.inline",
        "table.pipe",
        "table.pipe.outer",
        "table.widths.varied",
        "footnote.definition",
        "footnote.reference",
    }
)


def test_every_implemented_feature_is_referenced_by_code() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "dummy_md"
    corpus = ""
    for path in root.rglob("*.py"):
        relative = path.relative_to(root).as_posix()
        if relative in {"core/catalog.py", "core/features.py", "core/dialects.py"}:
            continue
        corpus += path.read_text(encoding="utf-8")
    missing = [
        feature_id
        for feature_id in IMPLEMENTED_IDS
        if feature_id not in _BASE_CASES and f'"{feature_id}"' not in corpus
    ]
    assert not missing, (
        "features marked implemented but never referenced by generator or "
        f"renderer code: {missing}"
    )


def test_registry_exposes_no_dead_payload_api() -> None:
    assert not hasattr(REGISTRY, "register_payload")


def test_frontmatter_options_have_no_unused_knobs() -> None:
    from dummy_md.elements import FrontMatterOptions

    context = build_context(
        dialect="extended",
        include=("frontmatter.yaml", "meta.title", "meta.tags"),
        options={"frontmatter": ElementRule(options=FrontMatterOptions(max_fields=1))},
    )
    block = REGISTRY.generator("frontmatter").generate(context)
    assert block.content.count("\n") == 0  # type: ignore[attr-defined]


def test_full_document_with_fixed_features_is_valid() -> None:
    spec = DocumentSpec(
        dialect="extended",
        seed=5,
        length=LengthSpec(4000),
        include=[
            "heading.*",
            "paragraph.*",
            "blockquote.*",
            "list.*",
            "table.*",
            "code.*",
            "math.*",
            "footnote.*",
        ],
    )
    text = Generator(spec).generate()
    assert text.startswith("#")
    assert len(text) >= 3500
    report = dummy_md.validate(text, "extended")
    assert report.ok


# --------------------------------------------------------------------------
# extended syntax added after the initial catalog
# --------------------------------------------------------------------------
def _paragraph_context(feature: str) -> GenerationContext:
    return build_context(
        dialect="extended",
        include=(feature,),
        options={
            "paragraph": ElementRule(
                options=ParagraphOptions(
                    min_sentences=2,
                    max_sentences=2,
                    sentence_min_words=6,
                    sentence_max_words=9,
                    inline_ratio=1.0,
                    emoji_ratio=0.0,
                    block_ratio=0.0,
                )
            )
        },
    )


@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("inline.superscript", "^"),
        ("inline.subscript", "~"),
        ("inline.underline", "++"),
        ("inline.highlight", "=="),
        ("inline.insert", "^^"),
        ("inline.emoji.shortcode", ":smile:"),
        ("inline.small_caps", "{.smallcaps}"),
    ],
)
def test_inline_variants_reach_output(feature: str, marker: str) -> None:
    context = _paragraph_context(feature)
    block = REGISTRY.generator("paragraph").generate(context)
    text = render_block(block, context)
    assert marker in text
    if feature == "inline.superscript":
        assert re.search(r"\^[^\s^]+\^", text)
    if feature == "inline.subscript":
        assert re.search(r"~[^\s~]+~", text)


@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("inline.critic.deletion", "{--"),
        ("inline.critic.insertion", "{++"),
        ("inline.critic.replacement", "~>"),
        ("inline.critic.highlight", "{=="),
        ("inline.critic.comment", "{>>"),
    ],
)
def test_critic_markup_reaches_output(feature: str, marker: str) -> None:
    context = _paragraph_context(feature)
    block = REGISTRY.generator("paragraph").generate(context)
    assert marker in render_block(block, context)


def test_abbreviation_definition_and_reference() -> None:
    definition_context = build_context(
        dialect="extended",
        include=("inline.abbreviation.definition",),
        options={"paragraph": ElementRule(options=ParagraphOptions(block_ratio=1.0))},
    )
    definition = REGISTRY.generator("paragraph").generate(definition_context)
    rendered = render_block(definition, definition_context)
    assert rendered.startswith("*[") and "]: " in rendered

    reference_context = build_context(
        dialect="extended",
        include=("inline.abbreviation.reference",),
        options={"paragraph": ElementRule(options=ParagraphOptions(block_ratio=0.0))},
        seed=3,
    )
    reference = REGISTRY.generator("paragraph").generate(reference_context)
    assert render_block(reference, reference_context).strip()


@pytest.mark.parametrize(
    ("feature", "marker"),
    [("paragraph.line_block", "| "), ("paragraph.fenced_div", ":::")],
)
def test_block_containers(feature: str, marker: str) -> None:
    context = build_context(
        dialect="extended",
        include=(feature,),
        options={"paragraph": ElementRule(options=ParagraphOptions(block_ratio=1.0))},
    )
    block = REGISTRY.generator("paragraph").generate(context)
    text = render_block(block, context)
    if feature == "paragraph.line_block":
        assert text.splitlines() and all(
            line.startswith("| ") for line in text.splitlines()
        )
    else:
        assert text.startswith("::: {") and text.rstrip().endswith(":::")


def test_theorem_block() -> None:
    context = build_context(
        dialect="extended",
        include=("theorem.block",),
        options={"paragraph": ElementRule(options=ParagraphOptions(block_ratio=1.0))},
    )
    block = REGISTRY.generator("paragraph").generate(context)
    text = render_block(block, context)
    assert "::: {.theorem" in text and "title=" in text


def test_definition_list() -> None:
    context = build_context(
        dialect="extended",
        include=("list.definition",),
        options={"list": ElementRule(options=ListOptions(definition_ratio=1.0))},
    )
    block = REGISTRY.generator("list").generate(context)
    text = render_block(block, context)
    lines = text.splitlines()
    assert lines and not lines[0].startswith(":")
    assert any(line.startswith(": ") for line in lines)


@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("list.ordered.alpha", "a. "),
        ("list.ordered.roman", "i. "),
        ("list.example_numbered", "(@) "),
    ],
)
def test_ordered_list_styles(feature: str, marker: str) -> None:
    context = build_context(dialect="extended", include=(feature,))
    block = REGISTRY.generator("list").generate(context)
    assert marker in render_block(block, context)


@pytest.mark.parametrize(
    ("features", "marker"),
    [
        (("link.wiki.basic",), "[["),
        (("link.wiki.basic", "link.wiki.alias"), "|"),
        (("link.wiki.basic", "link.wiki.heading"), "#"),
        (("link.wiki.basic", "link.wiki.block"), "#^"),
        (("link.inline", "link.attributes"), "){."),
    ],
)
def test_wiki_links_and_attributes(features: tuple[str, ...], marker: str) -> None:
    rendered = ""
    for seed in range(30):
        context = build_context(dialect="extended", include=features, seed=seed)
        block = REGISTRY.generator("link").generate(context)
        rendered = render_block(block, context)
        if marker in rendered:
            break
    assert marker in rendered
    if all(feature.startswith("link.wiki") for feature in features):
        assert "http" not in rendered
        if "link.wiki.alias" in features:
            assert re.search(r"\[\[[^\]|]+\|[^\]]+\]\]", rendered)
        if "link.wiki.heading" in features:
            assert re.search(r"\[\[[^\]#]+\#[^\]]+\]\]", rendered)
        if "link.wiki.block" in features:
            assert re.search(r"\[\[[^\]]+#\^[^\]]+\]\]", rendered)


@pytest.mark.parametrize(
    ("feature", "expected_style"),
    [("table.simple", "simple"), ("table.multiline", "multiline")],
)
def test_pandoc_table_styles(feature: str, expected_style: str) -> None:
    context = build_context(
        dialect="extended",
        include=(feature,),
        options={
            "table": ElementRule(
                options=TableOptions(
                    min_rows=2,
                    max_rows=2,
                    min_columns=2,
                    max_columns=2,
                    style_ratio=1.0,
                )
            )
        },
    )
    block = REGISTRY.generator("table").generate(context)
    assert isinstance(block, Table)
    assert block.style == expected_style
    text = render_block(block, context)
    assert "---" in text
    if expected_style == "simple":
        assert "|" not in text


def test_extended_generation_is_deterministic() -> None:
    from dummy_md import DocumentSpec, Generator, LengthSpec

    spec = DocumentSpec(
        dialect="extended",
        seed=13,
        length=LengthSpec(4000),
        include=[
            "paragraph.*",
            "list.*",
            "table.*",
            "link.*",
            "math.*",
            "diagram.*",
            "inline.*",
        ],
    )
    assert Generator(spec).generate() == Generator(spec).generate()


def test_empty_simple_table_falls_back_to_pipe() -> None:
    context = build_context(
        dialect="extended",
        include=("table.simple", "table.header_only"),
        options={
            "table": ElementRule(
                options=TableOptions(
                    style_ratio=1.0,
                    header_only_ratio=1.0,
                    min_columns=2,
                    max_columns=2,
                )
            )
        },
    )
    block = REGISTRY.generator("table").generate(context)
    assert isinstance(block, Table)
    text = render_block(block, context)
    assert "|" in text, "Pandoc simple tables need a body; fall back to pipe syntax"


def test_math_label_macros_and_crossref() -> None:
    label_context = build_context(
        dialect="extended",
        include=("math.display.dollar", "math.label"),
        options={"math": ElementRule(options={"label_ratio": 1.0})},
    )
    labelled = REGISTRY.generator("math").generate(label_context)
    assert "\\label{eq:" in render_block(labelled, label_context)

    macro_context = build_context(
        dialect="extended",
        include=("math.macros",),
        options={"math": ElementRule(options={"macro_ratio": 1.0})},
    )
    macros = REGISTRY.generator("math").generate(macro_context)
    assert "\\newcommand" in render_block(macros, macro_context)

    crossref_context = _paragraph_context("math.crossref")
    crossref = REGISTRY.generator("paragraph").generate(crossref_context)
    assert "[@eq:" in render_block(crossref, crossref_context)


def test_figure_label() -> None:
    context = build_context(
        dialect="extended",
        include=("image.figure.caption", "image.figure.label"),
        options={"image": ElementRule(options={"figure_ratio": 1.0})},
    )
    block = REGISTRY.generator("image").generate(context)
    text = render_block(block, context)
    assert text.count("![") == 1
    assert "{#fig:" in text
    assert "\n\n" not in text.strip(), (
        "caption must live in the image alt, not a second paragraph"
    )


@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("html.img", "<img "),
        ("html.picture", "<picture>"),
        ("html.audio", "<audio"),
        ("html.video", "<video"),
        ("html.iframe", "<iframe"),
        ("html.svg.inline", "<svg"),
        ("html.colgroup", "<colgroup>"),
        ("html.thead", "<thead>"),
        ("html.tbody", "<tbody>"),
        ("html.tfoot", "<tfoot>"),
        ("html.table.rowspan", 'rowspan="2"'),
        ("html.table.colspan", 'colspan="2"'),
        ("html.parsed_markdown", 'markdown="1"'),
    ],
)
def test_html_variants(feature: str, marker: str) -> None:
    context = build_context(dialect="extended", include=(feature,))
    block = REGISTRY.generator("html").generate(context)
    assert marker in render_block(block, context)


DIAGRAM_TOKENS: dict[str, str] = {
    "diagram.mermaid.swimlane": "flowchart LR",
    "diagram.mermaid.journey": "journey",
    "diagram.mermaid.quadrant": "quadrantChart",
    "diagram.mermaid.requirement": "requirementDiagram",
    "diagram.mermaid.c4": "C4Context",
    "diagram.mermaid.mindmap": "mindmap",
    "diagram.mermaid.timeline": "timeline",
    "diagram.mermaid.zenuml": "zenuml",
    "diagram.mermaid.sankey": "sankey-beta",
    "diagram.mermaid.xy": "xychart-beta",
    "diagram.mermaid.block": "block-beta",
    "diagram.mermaid.packet": "packet-beta",
    "diagram.mermaid.kanban": "kanban",
    "diagram.mermaid.architecture": "architecture-beta",
    "diagram.mermaid.radar": "radar-beta",
    "diagram.mermaid.eventmodeling": "eventmodeling",
    "diagram.mermaid.treemap": "treemap-beta",
    "diagram.mermaid.venn": "venn-beta",
    "diagram.mermaid.ishikawa": "ishikawa",
    "diagram.mermaid.wardley": "wardley-beta",
    "diagram.mermaid.treeview": "treeView-beta",
    "diagram.graphviz": "digraph",
    "diagram.plantuml": "@startuml",
    "diagram.d2": "->",
}


@pytest.mark.parametrize("feature", sorted(DIAGRAM_TOKENS))
def test_diagram_families(feature: str) -> None:
    context = build_context(dialect="extended", include=(feature,))
    block = REGISTRY.generator("diagram").generate(context)
    assert isinstance(block, CodeBlock)
    assert DIAGRAM_TOKENS[feature] in block.code
