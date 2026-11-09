from __future__ import annotations

import pytest
from markdown_it import MarkdownIt

from dummy_md.core.dialects import get_dialect
from dummy_md.core.nodes import (
    Attributes,
    Autolink,
    Blockquote,
    Callout,
    CharacterReference,
    CodeBlock,
    CodeSpan,
    Document,
    Emphasis,
    Escape,
    FootnoteDefinition,
    FootnoteReference,
    FrontMatter,
    Heading,
    HTMLBlock,
    Image,
    LineBreak,
    Link,
    LinkDefinition,
    ListBlock,
    ListItem,
    Math,
    MathBlock,
    Paragraph,
    RawHTML,
    Strikethrough,
    Table,
    TableCell,
    Text,
)
from dummy_md.exceptions import DialectError, RenderError
from dummy_md.renderers import CommonMarkRenderer, GFMRenderer, get_renderer
from dummy_md.renderers.base import escape_text, fence_for, format_destination

commonmark = CommonMarkRenderer(get_dialect("commonmark"))
gfm = GFMRenderer(get_dialect("gfm"))
extended = GFMRenderer(get_dialect("extended"))


def render_gfm(*blocks: object) -> str:
    return gfm.render(Document(children=blocks))  # type: ignore[arg-type]


def test_escape_text_modes() -> None:
    assert escape_text("a*b_c") == "a\\*b\\_c"
    assert escape_text("a|b", "table_cell") == "a\\|b"
    assert escape_text("a|b", "text") == "a|b"
    assert escape_text("[label]", "link_label") == "\\[label\\]"


def test_escape_line_start_hazards() -> None:
    assert escape_text("# not a heading", at_line_start=True) == "\\# not a heading"
    assert escape_text("1. not a list", at_line_start=True) == "1\\. not a list"
    assert escape_text("# fine", at_line_start=False) == "# fine"


def test_fence_selection_escalates() -> None:
    assert fence_for("plain") == ("`", 3)
    character, length = fence_for("``` inside")
    assert character == "~"
    assert length >= 3


def test_heading_atx_and_setext() -> None:
    doc = Document(
        children=(
            Heading(level=1, children=(Text("Title"),)),
            Heading(level=2, children=(Text("Sub"),), style="setext"),
            Heading(level=3, children=(Text("Closed"),), closed=True),
        )
    )
    assert gfm.render(doc) == "# Title\n\nSub\n---\n\n### Closed ###\n"


def test_heading_attributes_require_extended() -> None:
    heading = Heading(
        level=2, children=(Text("Section"),), attributes=Attributes(identifier="sec")
    )
    assert extended.render(Document(children=(heading,))).startswith(
        "## Section {#sec}"
    )
    with pytest.raises(DialectError, match="heading attributes"):
        gfm.render(Document(children=(heading,)))


def test_paragraph_line_breaks() -> None:
    doc = Document(
        children=(
            Paragraph(
                children=(
                    Text("first"),
                    LineBreak(hard=True, style="spaces"),
                    Text("second"),
                    LineBreak(hard=True, style="backslash"),
                    Text("third"),
                    LineBreak(hard=False, style="soft"),
                    Text("fourth"),
                )
            ),
        )
    )
    assert gfm.render(doc) == "first  \nsecond\\\nthird\nfourth\n"


def test_paragraph_escapes_line_starters() -> None:
    doc = Document(children=(Paragraph(children=(Text("# literal"),)),))
    assert gfm.render(doc) == "\\# literal\n"


def test_code_span_backtick_handling() -> None:
    doc = Document(
        children=(
            Paragraph(
                children=(
                    CodeSpan(code="plain"),
                    Text(" "),
                    CodeSpan(code="has ` tick"),
                    Text(" "),
                    CodeSpan(code="`edge"),
                )
            ),
        )
    )
    rendered = gfm.render(doc)
    assert "`plain`" in rendered
    assert "``has ` tick``" in rendered
    assert "`` `edge ``" in rendered


def test_fenced_code_escalates_when_body_contains_fence() -> None:
    block = CodeBlock(code="```\ninner\n```", info="markdown")
    rendered = gfm.render(Document(children=(block,)))
    assert rendered.startswith("~~~markdown")
    assert rendered.rstrip().endswith("~~~")


def test_indented_code_block() -> None:
    rendered = gfm.render(Document(children=(CodeBlock(code="x = 1", indented=True),)))
    assert rendered == "    x = 1\n"


def test_list_tight_and_loose() -> None:
    tight = ListBlock(
        items=(
            ListItem(children=(Paragraph(children=(Text("one"),)),)),
            ListItem(children=(Paragraph(children=(Text("two"),)),)),
        ),
        tight=True,
    )
    loose = ListBlock(
        items=(
            ListItem(children=(Paragraph(children=(Text("one"),)),)),
            ListItem(children=(Paragraph(children=(Text("two"),)),)),
        ),
        tight=False,
    )
    assert gfm.render(Document(children=(tight,))) == "- one\n- two\n"
    assert gfm.render(Document(children=(loose,))) == "- one\n\n- two\n"


def test_ordered_list_start_and_delimiter() -> None:
    block = ListBlock(
        ordered=True,
        delimiter=")",
        start=3,
        items=(ListItem(children=(Paragraph(children=(Text("third"),)),)),),
    )
    assert gfm.render(Document(children=(block,))) == "3) third\n"


def test_nested_list_indentation() -> None:
    inner = ListBlock(
        ordered=True,
        items=(ListItem(children=(Paragraph(children=(Text("nested"),)),)),),
    )
    outer = ListBlock(
        items=(
            ListItem(
                children=(Paragraph(children=(Text("outer"),)), inner),
            ),
        ),
    )
    assert gfm.render(Document(children=(outer,))).split("\n")[1] == "  1. nested"


def test_task_list_requires_gfm() -> None:
    block = ListBlock(
        items=(ListItem(children=(Paragraph(children=(Text("done"),)),), checked=True),)
    )
    assert gfm.render(Document(children=(block,))) == "- [x] done\n"
    with pytest.raises(DialectError, match="task lists"):
        commonmark.render(Document(children=(block,)))


def test_blockquote_prefixes_every_line() -> None:
    quote = Blockquote(
        children=(
            Paragraph(children=(Text("first"),)),
            Paragraph(children=(Text("second"),)),
        )
    )
    assert gfm.render(Document(children=(quote,))) == "> first\n>\n> second\n"


def test_strikethrough_is_gfm_only() -> None:
    para = Paragraph(children=(Strikethrough(children=(Text("gone"),)),))
    assert gfm.render(Document(children=(para,))) == "~~gone~~\n"
    with pytest.raises(DialectError, match="strikethrough"):
        commonmark.render(Document(children=(para,)))


def test_link_kinds() -> None:
    inline_link = Link(children=(Text("text"),), destination="https://example.com")
    titled = Link(
        children=(Text("t"),), destination="https://example.com", title="Title"
    )
    paren_title = Link(
        children=(Text("p"),),
        destination="https://example.com",
        title="Title",
        title_delimiter="(",
    )
    doc = Document(
        children=(
            Paragraph(children=(inline_link,)),
            Paragraph(children=(titled,)),
            Paragraph(children=(paren_title,)),
        )
    )
    rendered = gfm.render(doc)
    assert "[text](https://example.com)" in rendered
    assert '[t](https://example.com "Title")' in rendered
    assert "[p](https://example.com (Title))" in rendered


def test_reference_links_and_definitions() -> None:
    doc = Document(
        children=(
            Paragraph(
                children=(Link(children=(Text("see"),), kind="full", label="ref-1"),)
            ),
        ),
        link_definitions=(
            LinkDefinition(label="ref-1", destination="https://example.com"),
        ),
    )
    rendered = gfm.render(doc)
    assert "[see][ref-1]" in rendered
    assert "[ref-1]: https://example.com" in rendered


def test_shortcut_and_collapsed_links() -> None:
    doc = Document(
        children=(
            Paragraph(
                children=(
                    Link(kind="shortcut", label="a"),
                    Link(kind="collapsed", label="b"),
                )
            ),
        )
    )
    assert gfm.render(doc) == "[a][b][]\n"


def test_image_with_size_requires_extended() -> None:
    image = Image(alt=(Text("pic"),), destination="pic.png", width=320, height=200)
    rendered = extended.render(Document(children=(Paragraph(children=(image,)),)))
    assert rendered == "![pic](pic.png){width=320 height=200}\n"
    with pytest.raises(DialectError, match="width"):
        gfm.render(Document(children=(Paragraph(children=(image,)),)))


def test_autolink_and_character_reference() -> None:
    para = Paragraph(
        children=(
            Autolink(target="https://example.com"),
            Text(" "),
            CharacterReference(value="copy"),
            Escape(character="*"),
        )
    )
    assert gfm.render(Document(children=(para,))) == "<https://example.com> &copy;\\*\n"


def test_html_block_is_verbatim() -> None:
    block = HTMLBlock(block_type=6, content="<div>\n  <p>raw</p>\n</div>")
    assert gfm.render(Document(children=(block,))) == "<div>\n  <p>raw</p>\n</div>\n"


def test_inline_html_and_raw_text() -> None:
    para = Paragraph(children=(RawHTML(content="<kbd>Ctrl</kbd>"), Text(" pressed")))
    assert gfm.render(Document(children=(para,))) == "<kbd>Ctrl</kbd> pressed\n"


def test_pipe_table_rendering() -> None:
    table = Table(
        header=(
            TableCell(children=(Text("Name"),)),
            TableCell(children=(Text("Size"),)),
        ),
        rows=(
            (TableCell(children=(Text("alpha"),)), TableCell(children=(Text("12"),))),
        ),
        alignments=("left", "right"),
    )
    rendered = gfm.render(Document(children=(table,)))
    assert rendered.rstrip("\n").split("\n") == [
        "| Name  | Size |",
        "| :---- | ---: |",
        "| alpha |   12 |",
    ]


def test_table_without_outer_pipes() -> None:
    table = Table(
        header=(TableCell(children=(Text("A"),)), TableCell(children=(Text("B"),))),
        rows=(),
        alignments=("default", "center"),
        outer_pipes=False,
    )
    rendered = gfm.render(Document(children=(table,)))
    assert rendered.rstrip("\n").split("\n")[0] == "A   |  B "
    assert rendered.rstrip("\n").split("\n")[1] == "--- | :-:"


def test_table_cell_pipe_escaping() -> None:
    table = Table(
        header=(TableCell(children=(Text("a|b"),)),),
        rows=(),
        alignments=("left",),
    )
    rendered = gfm.render(Document(children=(table,)))
    assert "a\\|b" in rendered


def test_table_rejected_by_commonmark() -> None:
    table = Table(header=(TableCell(children=(Text("A"),)),), alignments=("left",))
    with pytest.raises(DialectError, match="pipe tables"):
        commonmark.render(Document(children=(table,)))


def test_table_spans_rejected() -> None:
    table = Table(
        header=(TableCell(children=(Text("A"),), colspan=2),),
        alignments=("left",),
    )
    with pytest.raises(DialectError, match="spans"):
        gfm.render(Document(children=(table,)))


def test_callout_rendering() -> None:
    callout = Callout(
        kind="note", title="Heads up", children=(Paragraph(children=(Text("body"),)),)
    )
    rendered = extended.render(Document(children=(callout,)))
    assert rendered.startswith("> [!NOTE] Heads up\n> body")
    with pytest.raises(DialectError, match="callouts"):
        gfm.render(Document(children=(callout,)))


def test_foldable_callout_markers() -> None:
    callout = Callout(kind="tip", children=(), foldable=True, collapsed=True)
    assert extended.render(Document(children=(callout,))).startswith("> [!TIP]-")


def test_footnotes_and_definitions() -> None:
    doc = Document(
        children=(Paragraph(children=(Text("Body"), FootnoteReference(label="1"))),),
        footnote_definitions=(
            FootnoteDefinition(
                label="1", children=(Paragraph(children=(Text("note"),)),)
            ),
        ),
    )
    rendered = extended.render(doc)
    assert "Body[^1]" in rendered
    assert "[^1]: note" in rendered
    with pytest.raises(DialectError, match="footnotes"):
        gfm.render(doc)


def test_math_blocks_and_inline_math() -> None:
    doc = Document(
        children=(
            Paragraph(children=(Text("Euler:"), Math(expression="e^{i\\pi}+1=0"))),
            MathBlock(expression="a^2 + b^2 = c^2"),
            MathBlock(expression="x = 1", delimiter="bracket"),
            MathBlock(expression="x = 1", environment="align"),
        )
    )
    rendered = extended.render(doc)
    assert "$e^{i\\pi}+1=0$" in rendered
    assert "$$\na^2 + b^2 = c^2\n$$" in rendered
    assert "\\[\nx = 1\n\\]" in rendered
    assert "\\begin{align}\nx = 1\n\\end{align}" in rendered


def test_frontmatter_formats() -> None:
    yaml = FrontMatter(format="yaml", content="title: Demo")
    toml = FrontMatter(format="toml", content='title = "Demo"')
    raw_json = FrontMatter(format="json", content='{\n"title": "Demo"\n}')
    doc = Document(children=(yaml, toml, raw_json, Paragraph(children=(Text("body"),))))
    rendered = extended.render(doc)
    assert "---\ntitle: Demo\n---" in rendered
    assert '+++\ntitle = "Demo"\n+++' in rendered
    assert '{\n"title": "Demo"\n}' in rendered


def test_renderer_rejects_unknown_dialect_renderer() -> None:
    with pytest.raises(LookupError):
        get_renderer(
            get_dialect("gfm").__class__(
                name="x", renderer="nope", features=frozenset()
            )
        )


def test_gfm_output_parses_with_markdown_it() -> None:
    doc = Document(
        children=(
            Heading(level=1, children=(Text("Title"),)),
            Paragraph(children=(Text("Hello "), Emphasis(children=(Text("world"),)))),
            Table(
                header=(
                    TableCell(children=(Text("A"),)),
                    TableCell(children=(Text("B"),)),
                ),
                rows=(
                    (
                        TableCell(children=(Text("1"),)),
                        TableCell(children=(Text("2"),)),
                    ),
                ),
                alignments=("left", "right"),
            ),
        )
    )
    parser = MarkdownIt("commonmark").enable("table")
    tokens = parser.parse(gfm.render(doc))
    kinds = [token.type for token in tokens]
    assert "heading_open" in kinds
    assert "table_open" in kinds


def test_commonmark_renderer_reports_unsupported_inline() -> None:
    with pytest.raises(RenderError):
        commonmark.render_inline(LineBreak())


def test_format_destination_variants() -> None:
    assert format_destination("") == ""
    assert format_destination("docs/a.md") == "docs/a.md"
    assert format_destination("a b.md") == "<a b.md>"
    assert format_destination("docs/a.md", title="T") == 'docs/a.md "T"'
