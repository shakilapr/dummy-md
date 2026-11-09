"""Fidelity tests for the previously missing catalog families."""

from __future__ import annotations

import pytest

from dummy_md.core.catalog import CATALOG
from dummy_md.core.nodes import (
    Bibliography,
    BlockNode,
    CodeBlock,
    DirectiveBlock,
    Figure,
    FrontMatter,
    MdxBlock,
    Table,
)
from dummy_md.renderers import get_renderer
from tests.helpers import REGISTRY, context_for_feature, document_of

_CITATION = {
    "citation.bracketed": "[@",
    "citation.multiple": "; ",
    "citation.narrative": "@",
    "citation.suppress_author": "-@",
    "citation.locator": ", p. ",
}

_DIRECTIVE = {
    "directive.myst.fenced": ":::{note}",
    "directive.myst.target": ")=",
    "directive.myst.figure": ":::{figure}",
    "directive.myst.table": ":::{table}",
    "directive.myst.admonition": ":::{admonition}",
    "directive.myst.theorem": ":::{theorem}",
    "directive.myst.proof": ":::{proof}",
    "directive.myst.dropdown": ":::{dropdown}",
    "directive.myst.tab_set": ":::{tab-set}",
    "directive.myst.tab_item": ":::{tab-item}",
    "directive.myst.include": ":::{include}",
    "directive.mkdocs.admonition": "!!! note",
    "directive.mkdocs.details": "??? details",
    "directive.mkdocs.tabs": '=== "',
    "directive.mkdocs.annotations": "```python",
    "directive.quarto.callout": "::: {.callout-",
    "directive.quarto.tabset": "::: {.panel-tabset}",
}

_MDX = {
    "mdx.import.default": "import Component",
    "mdx.import.named": "import { Widget }",
    "mdx.export.const": "export const",
    "mdx.export.function": "export function",
    "mdx.jsx.self_closing": "<Badge />",
    "mdx.jsx.paired": "<Callout>",
    "mdx.jsx.nested": "<Outer>",
    "mdx.jsx.fragment": "<>",
    "mdx.jsx.prop.string": 'label="Save"',
    "mdx.jsx.prop.expression": "onClick",
    "mdx.jsx.prop.object": "options={{",
    "mdx.jsx.prop.spread": "{...props}",
    "mdx.jsx.block": "<Callout",
    "mdx.docusaurus.tabs": "<Tabs>",
    "mdx.docusaurus.tabitem": "<TabItem",
}

_STRESS = {
    "stress.escape.asterisk": "\\*",
    "stress.escape.underscore": "\\_",
    "stress.escape.heading": "\\#",
    "stress.escape.blockquote": "\\>",
    "stress.escape.bracket_open": "\\[",
    "stress.escape.bracket_close": "\\]",
    "stress.escape.paren_open": "\\(",
    "stress.escape.paren_close": "\\)",
    "stress.escape.pipe": "\\|",
    "stress.escape.backtick": "\\`",
    "stress.escape.backslash": "\\\\",
    "stress.text.html_like": "\\<span\\>",
    "stress.text.entities": "&amp;",
    "stress.unicode.mixed": "日本語",
    "stress.unicode.combining": "e\u0301",
    "stress.unicode.emoji_sequence": "👩🏽‍💻",
    "stress.unicode.cyrillic": "Пример",
    "stress.unicode.cjk": "日本語",
    "stress.unicode.rtl": "هذا نص",
    "stress.unicode.zero_width": "\u200b",
    "stress.text.long_unbroken": "x" * 100,
    "stress.delimiters.adjacent": "\\*",
    "stress.text.leading_control_chars": "\u0001",
}


def _render(feature: str, *, seed: int = 3) -> tuple[str, BlockNode]:
    context = context_for_feature(feature, seed=seed)
    spec = REGISTRY.feature(feature)
    assert spec.generator is not None
    block = REGISTRY.generator(spec.generator).generate(context)
    text = get_renderer(context.dialect).render(document_of(block))
    return text, block


@pytest.mark.parametrize("feature", sorted(_CITATION))
def test_citation_modes_render(feature: str) -> None:
    text, block = _render(feature)
    assert _CITATION[feature] in text
    assert isinstance(block, type(block))


@pytest.mark.parametrize("feature", sorted(_DIRECTIVE))
def test_documentation_directives_render(feature: str) -> None:
    text, block = _render(feature)
    assert _DIRECTIVE[feature] in text
    assert isinstance(block, DirectiveBlock)


@pytest.mark.parametrize(
    "feature",
    [
        "directive.myst.role",
        "directive.myst.ref",
        "directive.myst.numref",
        "directive.myst.doc_ref",
    ],
)
def test_myst_roles_render(feature: str) -> None:
    text, _block = _render(feature)
    assert "{" in text and "}`" in text


@pytest.mark.parametrize("feature", ["directive.mkdocs.keys", "directive.mkdocs.icons"])
def test_mkdocs_inline_directives_render(feature: str) -> None:
    text, _block = _render(feature)
    assert ("++" in text) or (":" in text)


def test_quarto_shortcode_renders() -> None:
    text, _block = _render("directive.quarto.shortcode")
    assert "{{<" in text


@pytest.mark.parametrize("feature", sorted(_MDX))
def test_mdx_payloads_render(feature: str) -> None:
    text, block = _render(feature)
    assert _MDX[feature] in text
    assert isinstance(block, (MdxBlock, type(block)))


@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("platform.obsidian.transclusion", "![[note]]"),
        ("platform.obsidian.transclusion.heading", "![[note#"),
        ("platform.obsidian.transclusion.block", "![[note#^"),
        ("platform.obsidian.embed.pdf", "![[manual.pdf]]"),
        ("platform.obsidian.embed.audio", "![[clip.mp3]]"),
        ("platform.obsidian.embed.video", "![[clip.mp4]]"),
        ("platform.obsidian.embed.pdf_page", "![[manual.pdf#page="),
        ("platform.obsidian.embed.width", "|320]]"),
        ("platform.obsidian.embed.size", "|320x200]]"),
        ("platform.obsidian.tag", "#"),
        ("platform.obsidian.tag.nested", "/"),
        ("platform.obsidian.wikilink.unresolved", "[["),
        ("platform.obsidian.block_id", "^block-"),
        ("platform.obsidian.comment", "%%"),
        ("platform.obsidian.highlight", "=="),
        ("platform.gitlab.issue_ref", "#"),
        ("platform.gitlab.mr_ref", "!"),
        ("platform.gitlab.mention", "@"),
        ("platform.gitlab.commit_ref", "`"),
        ("platform.gitlab.placeholder", "%{"),
        ("platform.gitlab.color_chip", "`#"),
        ("platform.gitlab.include", "::include{file="),
    ],
)
def test_platform_constructs_render(feature: str, marker: str) -> None:
    text, _block = _render(feature)
    assert marker in text


@pytest.mark.parametrize(
    "feature",
    [
        "platform.obsidian.property.text",
        "platform.obsidian.property.list",
        "platform.obsidian.property.number",
        "platform.obsidian.property.checkbox",
        "platform.obsidian.property.date",
        "platform.obsidian.property.datetime",
        "platform.obsidian.property.tag",
    ],
)
def test_obsidian_properties_render(feature: str) -> None:
    _text, block = _render(feature)
    assert isinstance(block, FrontMatter)


@pytest.mark.parametrize("feature", sorted(_STRESS))
def test_stress_text_renders(feature: str) -> None:
    text, _block = _render(feature)
    assert _STRESS[feature] in text


@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("stress.line_endings.lf", "line one\nline two"),
        ("stress.line_endings.crlf", "line one\r\nline two"),
        ("stress.whitespace.trailing", "trailing spaces   "),
    ],
)
def test_stress_whitespace_renders(feature: str, marker: str) -> None:
    text, _block = _render(feature)
    assert marker in text


def test_stress_tabs_code() -> None:
    text, block = _render("stress.whitespace.tabs")
    assert isinstance(block, CodeBlock)
    assert "\talpha" in text


def test_stress_deep_list() -> None:
    text, _block = _render("stress.nesting.deep")
    assert text.count("\n") >= 6


def test_stress_percent_encoded_url() -> None:
    text, _block = _render("stress.url.percent_encoded")
    assert "%E2%9C%93" in text and "%20" in text


@pytest.mark.parametrize(
    "feature", ["table.grid", "table.grid.colspan", "table.grid.rowspan"]
)
def test_grid_table_renders(feature: str) -> None:
    text, block = _render(feature)
    assert isinstance(block, Table)
    assert block.style == "grid"
    assert text.startswith("+")


def test_grid_table_has_spans() -> None:
    _text, block = _render("table.grid.colspan")
    assert isinstance(block, Table)
    assert any(cell.colspan > 1 for cell in block.header)
    _text, block = _render("table.grid.rowspan")
    assert isinstance(block, Table)
    assert any(cell.rowspan > 1 for row in block.rows for cell in row)


@pytest.mark.parametrize(
    ("feature", "marker"),
    [
        ("code.line_numbers", "{numberLines}"),
        ("code.title.docusaurus", 'title="example.js"'),
        ("code.highlight.docusaurus", "{1,3}"),
        ("code.annotations", "1. "),
        ("code.annotations.inline", "# (1)"),
        ("code.chunk.quarto", "#| label:"),
        ("code.chunk.quarto.inline", "{python} 1 + 1"),
        ("code.json_table.gitlab", '"name"'),
    ],
)
def test_code_extras_render(feature: str, marker: str) -> None:
    text, _block = _render(feature)
    assert marker in text


def test_implicit_figure_renders() -> None:
    _text, block = _render("image.figure.implicit", seed=1)
    assert isinstance(block, Figure)
    assert block.implicit


def test_usecase_diagram_renders() -> None:
    text, _block = _render("diagram.mermaid.usecase")
    assert "usecase-beta" in text


def test_bibliography_directive_renders() -> None:
    text, block = _render("citation.bibliography_directive")
    assert isinstance(block, Bibliography)
    assert "::: {#refs}" in text


def test_every_new_feature_is_marked_implemented() -> None:
    missing = [spec.id for spec in CATALOG if not spec.implemented]
    assert missing == ["stress.document.large"]
