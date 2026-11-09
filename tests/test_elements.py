from __future__ import annotations

import re

import pytest
from markdown_it import MarkdownIt

from dummy_md.config import ElementRule
from dummy_md.core.catalog import IMPLEMENTED_IDS
from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    Callout,
    CodeBlock,
    Document,
    Figure,
    FrontMatter,
    Heading,
    HTMLBlock,
    Image,
    ListBlock,
    MathBlock,
    Paragraph,
    Table,
    Text,
    ThematicBreak,
)
from dummy_md.elements import HeadingOptions, ImageOptions, ListOptions, TableOptions
from dummy_md.elements.code import CodeOptions
from dummy_md.exceptions import ConfigurationError, DialectError
from dummy_md.renderers import get_renderer
from tests.helpers import (
    REGISTRY,
    build_context,
    context_for_feature,
    document_of,
    generate_block,
)

PARSER = MarkdownIt("commonmark").enable("table")


def render_context(context: GenerationContext, family: str) -> str:
    generator = REGISTRY.generator(family)
    block = generator.generate(context)
    return get_renderer(context.dialect).render(document_of(block))


# -- headings ----------------------------------------------------------------
def test_heading_levels_are_valid() -> None:
    for seed in range(30):
        block = generate_block("heading", seed=seed)
        assert isinstance(block, Heading)
        assert 1 <= block.level <= 6


def test_heading_attributes_only_in_extended() -> None:
    found = ""
    for seed in range(40):
        context = build_context(
            dialect="extended",
            include=("heading.attributes.identifier", "heading.attributes.classes"),
            seed=seed,
        )
        rendered = render_context(context, "heading")
        if "{" in rendered:
            found = rendered
            break
    assert found, "expected at least one heading with attributes"
    assert "#" in found


def test_heading_tracker_prevents_skips() -> None:
    context = build_context(include=("heading.atx.h6",), max_depth=1)
    context.headings.last_level = 2
    block = REGISTRY.generator("heading").generate(context)
    assert isinstance(block, Heading)
    assert block.level <= 3


def test_heading_options_override() -> None:
    context = build_context(
        include=("heading.atx.h1", "heading.atx.h2"),
        options={"heading": ElementRule(options=HeadingOptions(style="atx"))},
    )
    block = REGISTRY.generator("heading").generate(context)
    assert isinstance(block, Heading)
    assert block.style == "atx"


def test_heading_rejects_unknown_option_type() -> None:
    context = build_context(
        include=("heading.atx.h1",),
        options={"heading": ElementRule(options=ListOptions())},
    )
    with pytest.raises(ConfigurationError, match="HeadingOptions"):
        REGISTRY.generator("heading").generate(context)


# -- paragraphs --------------------------------------------------------------
def test_paragraph_text_is_placeholder_prose() -> None:
    block = generate_block("paragraph", seed=1)
    assert isinstance(block, Paragraph)
    text = "".join(node.content for node in block.children if isinstance(node, Text))
    assert text.strip()
    assert "\n" not in text


def test_paragraph_inline_features_appear() -> None:
    writes = 0
    for seed in range(20):
        context = build_context(
            include=("inline.strong.asterisk", "inline.code_span"), seed=seed
        )
        block = REGISTRY.generator("paragraph").generate(context)
        assert isinstance(block, Paragraph)
        rendered = get_renderer(context.dialect).render(document_of(block))
        if "**" in rendered or "`" in rendered:
            writes += 1
    assert writes > 0


def test_paragraph_line_breaks_rendered() -> None:
    rendered = render_context(
        build_context(
            include=("paragraph.multi_line", "paragraph.linebreak.hard_spaces"),
            seed=4,
        ),
        "paragraph",
    )
    assert rendered.count("\n") >= 1


# -- thematic breaks ---------------------------------------------------------
def test_thematic_break_characters() -> None:
    seen = set()
    for seed in range(20):
        block = generate_block(
            "thematic_break",
            include=(
                "thematic_break.hyphen",
                "thematic_break.asterisk",
                "thematic_break.underscore",
            ),
            seed=seed,
        )
        assert isinstance(block, ThematicBreak)
        seen.add(block.character)
    assert seen == {"-", "*", "_"}


# -- lists -------------------------------------------------------------------
def test_list_structure_and_markers() -> None:
    block = generate_block(
        "list",
        include=(
            "list.unordered.hyphen",
            "list.ordered.dot",
            "list.nested.unordered",
            "list.nested.ordered",
        ),
        seed=2,
    )
    assert isinstance(block, ListBlock)
    assert len(block.items) >= 2
    for item in block.items:
        assert item.children
        assert isinstance(item.children[0], Paragraph)


def test_task_items_only_with_gfm_features() -> None:
    block = generate_block(
        "list", include=("list.task.checked", "list.task.unchecked"), seed=7
    )
    assert isinstance(block, ListBlock)
    assert any(item.checked is not None for item in block.items)


def test_commonmark_rejects_task_lists() -> None:
    context = build_context(
        include=("list.task.checked",),
        seed=1,
        options={"list": ElementRule(options=ListOptions(task_ratio=1.0))},
    )
    block = REGISTRY.generator("list").generate(context)
    commonmark = build_context(dialect="commonmark")
    with pytest.raises(DialectError, match="task lists"):
        get_renderer(commonmark.dialect).render(document_of(block))


def test_nested_lists_respect_max_depth() -> None:
    context = build_context(
        include=("list.unordered.hyphen", "list.nested.unordered"),
        max_depth=1,
        seed=5,
    )
    block = REGISTRY.generator("list").generate(context)
    assert isinstance(block, ListBlock)

    def depth_of(node: ListBlock, depth: int = 1) -> int:
        deepest = depth
        for item in node.items:
            for child in item.children:
                if isinstance(child, ListBlock):
                    deepest = max(deepest, depth_of(child, depth + 1))
        return deepest

    assert depth_of(block) <= 1


def test_loose_lists_have_multi_block_items() -> None:
    context = build_context(
        include=(
            "list.unordered.hyphen",
            "list.loose",
            "list.item.multiple_paragraphs",
        ),
        seed=3,
        options={
            "list": ElementRule(
                options=ListOptions(multi_paragraph_ratio=1.0, extra_block_ratio=0.0)
            )
        },
    )
    block = REGISTRY.generator("list").generate(context)
    assert isinstance(block, ListBlock)
    assert not block.tight
    assert all(len(item.children) > 1 for item in block.items)


# -- tables ------------------------------------------------------------------
def test_table_shape_and_alignments() -> None:
    block = generate_block(
        "table",
        include=(
            "table.pipe",
            "table.align.left",
            "table.align.right",
            "table.align.center",
            "table.align.mixed",
        ),
        seed=6,
    )
    assert isinstance(block, Table)
    assert len(block.alignments) == len(block.header)
    assert all(len(row) >= 1 for row in block.rows)


def test_table_rows_and_columns_options() -> None:
    context = build_context(
        include=("table.pipe", "table.align.left"),
        options={
            "table": ElementRule(
                options=TableOptions(
                    min_rows=3, max_rows=3, min_columns=2, max_columns=2
                )
            )
        },
    )
    block = REGISTRY.generator("table").generate(context)
    assert isinstance(block, Table)
    assert len(block.header) == 2
    assert len(block.rows) == 3


def test_table_cells_are_inline_only() -> None:
    block = generate_block("table", include=("table.pipe", "table.cell.bold"), seed=8)
    assert isinstance(block, Table)
    for cell in (*block.header, *(c for row in block.rows for c in row)):
        assert all(not isinstance(child, Paragraph) for child in cell.children)


def test_table_rendering_parses_as_table() -> None:
    context = build_context(include=("table.pipe", "table.align.default"), seed=9)
    rendered = render_context(context, "table")
    tokens = PARSER.parse(rendered)
    assert any(token.type == "table_open" for token in tokens)


# -- code --------------------------------------------------------------------
def test_code_payload_matches_language() -> None:
    for _ in range(10):
        block = generate_block("code", include=("code.payload.python",), seed=11)
        assert isinstance(block, CodeBlock)
        assert "def " in block.code


def test_fenced_code_renders_with_info_string() -> None:
    context = build_context(
        include=("code.fenced.backtick", "code.info", "code.payload.json"),
        seed=2,
        options={"code": ElementRule(options=CodeOptions(info_ratio=1.0))},
    )
    rendered = render_context(context, "code")
    assert rendered.startswith("```json")


def test_code_fence_escalates_for_backtick_payload() -> None:
    context = build_context(
        include=("code.fenced.backtick", "code.payload.backticks"), seed=2
    )
    rendered = render_context(context, "code")
    assert rendered.startswith("~~~")


def test_code_attributes_only_in_extended() -> None:
    context = build_context(
        dialect="extended",
        include=("code.fenced.backtick", "code.attributes.identifier"),
        seed=1,
        options={"code": ElementRule(options=CodeOptions(attribute_ratio=1.0))},
    )
    rendered = render_context(context, "code")
    assert "{" in rendered


def test_code_options_control_style() -> None:
    context = build_context(
        include=("code.indented",),
        options={"code": ElementRule(options=CodeOptions(indented_ratio=1.0))},
    )
    block = REGISTRY.generator("code").generate(context)
    assert isinstance(block, CodeBlock)
    assert block.indented


# -- links -------------------------------------------------------------------
def test_link_reference_definitions_close_over_usage() -> None:
    context = build_context(
        include=(
            "link.reference.full",
            "link.reference.collapsed",
            "link.reference.shortcut",
            "link.definition",
            "link.definition.shared",
        ),
        seed=5,
    )
    context.rng.seed(5)
    block = REGISTRY.generator("link").generate(context)
    rendered = get_renderer(context.dialect).render(
        Document(
            children=(block,),
            link_definitions=tuple(context.refs.links.values()),
        )
    )
    labels = set(context.refs.links)
    assert labels
    for label in labels:
        assert f"[{label}]" in rendered
        assert f"[{label}]:" in rendered


def test_link_autolinks_are_bare_when_gfm() -> None:
    context = build_context(include=("link.autolink.bare_url",), seed=1)
    rendered = render_context(context, "link")
    assert "<http" not in rendered
    assert "http" in rendered


def test_link_commonmark_rejects_bare_autolink_feature() -> None:
    with pytest.raises(DialectError):
        build_context(dialect="commonmark", include=("link.autolink.bare_url",))


# -- images ------------------------------------------------------------------
def test_image_variants() -> None:
    block = generate_block(
        "image",
        include=("image.inline", "image.url.remote", "image.alt"),
        seed=1,
    )
    assert isinstance(block, Paragraph)
    assert any(isinstance(node, Image) for node in block.children)


def test_image_figure_uses_figure_node() -> None:
    context = build_context(
        dialect="extended",
        include=("image.figure.caption",),
        seed=2,
        options={"image": ElementRule(options=ImageOptions(figure_ratio=1.0))},
    )
    block = REGISTRY.generator("image").generate(context)
    assert isinstance(block, Figure)
    rendered = get_renderer(context.dialect).render(document_of(block))
    assert "![" in rendered


def test_image_in_table_produces_table() -> None:
    block = generate_block("image", include=("image.in_table",), seed=3)
    assert isinstance(block, Table)


# -- quotes and callouts -----------------------------------------------------
def test_blockquote_variants_render() -> None:
    context = build_context(include=("blockquote.single", "blockquote.nested"), seed=4)
    rendered = render_context(context, "blockquote")
    assert rendered.startswith("> ")


def test_callout_kinds_come_from_active_features() -> None:
    context = build_context(
        dialect="extended", include=("callout.github.warning",), seed=1
    )
    block = REGISTRY.generator("callout").generate(context)
    assert isinstance(block, Callout)
    assert block.kind == "warning"


def test_nested_callout() -> None:
    context = build_context(
        dialect="extended", include=("callout.obsidian.note", "callout.nested"), seed=2
    )
    block = REGISTRY.generator("callout").generate(context)
    for _ in range(20):
        block = REGISTRY.generator("callout").generate(context)
        if isinstance(block, Callout) and any(
            isinstance(child, Callout) for child in block.children
        ):
            break
    rendered = get_renderer(context.dialect).render(document_of(block))
    assert rendered.startswith("> [!NOTE]")


# -- html --------------------------------------------------------------------
def test_html_blocks_are_verbatim() -> None:
    block = generate_block("html", include=("html.comment",), seed=1)
    assert isinstance(block, HTMLBlock)
    rendered = get_renderer(build_context().dialect).render(document_of(block))
    assert rendered.startswith("<!--")


def test_html_details_template() -> None:
    block = generate_block("html", include=("html.details",), seed=1)
    assert isinstance(block, HTMLBlock)
    assert "<details>" in block.content


# -- footnotes ---------------------------------------------------------------
def test_footnote_closure() -> None:
    context = build_context(dialect="extended", include=("footnote.reference",), seed=1)
    block = REGISTRY.generator("footnote").generate(context)
    assert isinstance(block, Paragraph)
    assert len(context.refs.footnotes) == 1
    label = next(iter(context.refs.footnotes))
    assert any(getattr(node, "label", None) == label for node in block.children)


# -- math --------------------------------------------------------------------
def test_math_environments() -> None:
    for feature, environment in (
        ("math.latex.align", "align"),
        ("math.latex.cases", "cases"),
        ("math.latex.matrix", "matrix"),
    ):
        block = generate_block("math", dialect="extended", include=(feature,), seed=1)
        assert isinstance(block, MathBlock)
        assert block.environment == environment


def test_math_fence_is_code_block() -> None:
    block = generate_block("math", dialect="extended", include=("math.fence",), seed=1)
    assert isinstance(block, CodeBlock)
    assert block.info == "math"


# -- diagrams ----------------------------------------------------------------
@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("diagram.mermaid.flowchart", "flowchart"),
        ("diagram.mermaid.sequence", "sequenceDiagram"),
        ("diagram.mermaid.gantt", "gantt"),
        ("diagram.mermaid.er", "erDiagram"),
    ],
)
def test_diagram_bodies(feature: str, marker: str) -> None:
    block = generate_block("diagram", dialect="extended", include=(feature,), seed=1)
    assert isinstance(block, CodeBlock)
    assert block.info == "mermaid"
    assert marker in block.code


# -- front matter ------------------------------------------------------------
def test_frontmatter_formats_render() -> None:
    for feature in ("frontmatter.yaml", "frontmatter.toml", "frontmatter.json"):
        block = generate_block(
            "frontmatter", dialect="extended", include=(feature,), seed=1
        )
        assert isinstance(block, FrontMatter)
        assert block.content


def test_frontmatter_fields_follow_active_meta_features() -> None:
    block = generate_block(
        "frontmatter",
        dialect="extended",
        include=("frontmatter.yaml", "meta.title", "meta.tags"),
        seed=1,
    )
    assert isinstance(block, FrontMatter)
    assert "title:" in block.content
    assert "tags:" in block.content


def test_frontmatter_documents_are_well_formed() -> None:
    import json

    block = generate_block(
        "frontmatter", dialect="extended", include=("frontmatter.json",), seed=4
    )
    assert isinstance(block, FrontMatter)
    assert isinstance(json.loads(block.content), dict)

    rendered = get_renderer(build_context(dialect="extended").dialect).render(
        document_of(block)
    )
    assert rendered.count("{") == rendered.count("}") == 1

    yaml_block = generate_block(
        "frontmatter", dialect="extended", include=("frontmatter.yaml",), seed=4
    )
    assert isinstance(yaml_block, FrontMatter)
    rendered_yaml = get_renderer(build_context(dialect="extended").dialect).render(
        document_of(yaml_block)
    )
    assert rendered_yaml.startswith("---\n")


# -- whole-catalog smoke -----------------------------------------------------
def test_every_implemented_feature_generates_and_parses() -> None:
    families = sorted(
        {
            generator
            for feature_id in IMPLEMENTED_IDS
            if (generator := REGISTRY.feature(feature_id).generator) is not None
        }
    )
    assert families
    failures: list[str] = []
    for feature_id in IMPLEMENTED_IDS:
        spec = REGISTRY.feature(feature_id)
        if spec.generator is None:
            continue
        try:
            context = context_for_feature(feature_id, seed=13)
            context.rng.seed(13)
            block = REGISTRY.generator(spec.generator).generate(context)
            document = document_of(block)
            if spec.family == "frontmatter":
                pass
            text = get_renderer(context.dialect).render(document)
            PARSER.parse(text)
        except Exception as error:  # noqa: BLE001 - report, do not stop
            failures.append(f"{feature_id}: {type(error).__name__}: {error}")
    assert not failures, "\n".join(failures)


def test_registry_validates_all_generators() -> None:
    REGISTRY.validate()


def test_no_implemented_feature_is_unknown() -> None:
    for feature_id in IMPLEMENTED_IDS:
        assert REGISTRY.feature(feature_id).implemented
        assert re.match(r"^[a-z][a-z0-9_.]+$", feature_id)
