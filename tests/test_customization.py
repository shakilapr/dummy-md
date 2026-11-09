from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from random import Random

import pytest

import dummy_md
from dummy_md import DocumentSpec, ElementRule, Generator, LengthSpec
from dummy_md.cli import main, parse_weights
from dummy_md.config import LineEnding
from dummy_md.core.budget import count_words, measure_text
from dummy_md.core.nodes import (
    Callout,
    CodeBlock,
    Document,
    FrontMatter,
    ListBlock,
    MathBlock,
    Paragraph,
    Table,
    ThematicBreak,
)
from dummy_md.core.registry import Registry
from dummy_md.elements import (
    OPTION_TYPES,
    CodeOptions,
    DiagramOptions,
    FrontMatterOptions,
    HeadingOptions,
    LinkOptions,
    ListOptions,
    MathOptions,
    ParagraphOptions,
    TableOptions,
    ThematicBreakOptions,
    build_generators,
    build_options,
)
from dummy_md.exceptions import ConfigurationError, DialectError
from dummy_md.presets import PRESETS, Preset, register_preset
from dummy_md.renderers import GFMRenderer, get_renderer
from dummy_md.text import TEXT_PROVIDERS, register_text_style
from tests.helpers import REGISTRY, build_context

# --------------------------------------------------------------------------
# registry & custom dialects
# --------------------------------------------------------------------------


def new_registry() -> Registry:
    registry = Registry()
    for generator in build_generators().values():
        registry.register_generator(generator)
    return registry


def test_custom_dialect_adds_capability() -> None:
    registry = new_registry()
    dialect = registry.add_dialect("docs", base="gfm", add=["math.display.dollar"])
    assert "math.display.dollar" in dialect.features
    assert dialect.base == "gfm"

    spec = DocumentSpec(
        dialect="docs", seed=1, include=["math.display.dollar"], length=LengthSpec(400)
    )
    text = Generator(spec, registry).generate()
    assert "$$" in text
    assert dummy_md.validate(text).ok


def test_custom_dialect_removes_capability() -> None:
    registry = new_registry()
    registry.add_dialect("plain", base="gfm", remove=["table.pipe"])
    with pytest.raises(DialectError):
        registry.resolve(dialect="plain", include=["table.pipe"])


def test_custom_dialect_glob_filters_removed_feature() -> None:
    registry = new_registry()
    registry.add_dialect("no-html", base="gfm", remove=["html.block", "html.inline"])
    selected = registry.resolve(dialect="no-html", include=["html.*"])
    assert "html.block" not in selected
    assert "html.comment" in selected


def test_custom_dialect_rejects_unknown_or_unimplemented() -> None:
    registry = new_registry()
    with pytest.raises(ConfigurationError, match="unknown feature"):
        registry.add_dialect("bad", add=["nope.feature"])
    with pytest.raises(ConfigurationError, match="unimplemented"):
        registry.add_dialect("bad", add=["table.grid"])


def test_custom_dialect_rejects_removing_missing_feature() -> None:
    registry = new_registry()
    with pytest.raises(ConfigurationError, match="does not provide"):
        registry.add_dialect("bad", base="gfm", remove=["table.grid"])


def test_custom_dialect_rejects_add_and_remove_overlap() -> None:
    registry = new_registry()
    with pytest.raises(ConfigurationError, match="added and removed"):
        registry.add_dialect(
            "bad", base="gfm", add=["table.pipe"], remove=["table.pipe"]
        )


def test_duplicate_dialect_requires_replace() -> None:
    registry = new_registry()
    registry.add_dialect("docs", base="gfm")
    with pytest.raises(ConfigurationError, match="already registered"):
        registry.add_dialect("docs", base="gfm")
    replacement = registry.add_dialect(
        "docs", base="gfm", remove=["table.pipe"], replace=True
    )
    assert "table.pipe" not in replacement.features


def test_register_dialect_requires_registered_renderer() -> None:
    registry = new_registry()
    with pytest.raises(ConfigurationError, match="renderer"):
        registry.add_dialect("broken", base="gfm", renderer="missing")


def test_custom_dialect_with_custom_renderer() -> None:
    class ExcitedRenderer(GFMRenderer):
        def _heading(self, node: object) -> str:
            return super()._heading(node) + "!"  # type: ignore[arg-type]

    registry = new_registry()
    registry.register_renderer("excited", ExcitedRenderer)
    registry.add_dialect("loud", base="gfm", renderer="excited")
    spec = DocumentSpec(dialect="loud", seed=2, length=LengthSpec(300))
    text = Generator(spec, registry).generate()
    assert text.startswith("# ")
    assert text.splitlines()[0].endswith("!")


def test_duplicate_renderer_requires_replace() -> None:
    registry = new_registry()
    with pytest.raises(ConfigurationError, match="already registered"):
        registry.register_renderer("gfm", GFMRenderer)
    registry.register_renderer("gfm", GFMRenderer, replace=True)


def test_validate_checks_renderers() -> None:
    registry = Registry(renderers={})
    dummy_md.elements.register(registry)
    with pytest.raises(ConfigurationError, match="renderer"):
        registry.validate()


# --------------------------------------------------------------------------
# feature weights
# --------------------------------------------------------------------------


def test_feature_weight_biases_variant_selection() -> None:
    context = build_context(
        include=("inline.emphasis.asterisk", "inline.strong.asterisk"),
        feature_weights={"inline.emphasis.asterisk": 10_000.0},
        seed=4,
    )
    generator = REGISTRY.generator("paragraph")
    rendered = [
        get_renderer(context.dialect).render(
            Document(children=(generator.generate(context),))
        )
        for _ in range(20)
    ]
    joined = "".join(rendered)
    assert "*" in joined
    assert "**" not in joined


def test_feature_weight_reproducible() -> None:
    first = dummy_md.generate(
        length=600, seed=8, feature_weights={"inline.emphasis.asterisk": 5.0}
    )
    second = dummy_md.generate(
        length=600, seed=8, feature_weights={"inline.emphasis.asterisk": 5.0}
    )
    assert first == second


def test_unknown_feature_weight_errors() -> None:
    with pytest.raises(ConfigurationError, match="unknown feature"):
        dummy_md.generate(length=100, feature_weights={"nope.feature": 2.0})


def test_non_positive_feature_weight_rejected() -> None:
    with pytest.raises(ConfigurationError, match="positive"):
        DocumentSpec(feature_weights={"heading.atx.h1": 0.0})


def test_callout_weight_selects_kind() -> None:
    context = build_context(
        dialect="extended",
        include=("callout.github.note", "callout.github.warning"),
        feature_weights={"callout.github.warning": 10_000.0},
        seed=3,
    )
    kinds = {
        REGISTRY.generator("callout").generate(context).kind  # type: ignore[attr-defined]
        for _ in range(15)
    }
    assert kinds == {"warning"}


# --------------------------------------------------------------------------
# specification serialization
# --------------------------------------------------------------------------


def sample_spec() -> DocumentSpec:
    return DocumentSpec(
        dialect="extended",
        seed=11,
        text_seed=12,
        length=LengthSpec(value=900, unit="chars", mode="approximate", tolerance=0.1),
        include=("heading.*", "paragraph.*"),
        exclude=("table.*",),
        elements={
            "heading": ElementRule(
                min_count=2,
                max_count=5,
                weight=2.0,
                options=HeadingOptions(style="atx", levels=(1, 2)),
            ),
            "paragraph": ElementRule(weight=5.0),
        },
        feature_weights={"inline.emphasis.asterisk": 3.0},
        text_style="lorem",
        max_nesting_depth=2,
        heading_skeleton=False,
        include_frontmatter=False,
        line_ending="crlf",
        trailing_newline=False,
        section_chars=2_000,
        fill_ratio=0.75,
    )


def test_spec_round_trips_through_dict() -> None:
    spec = sample_spec()
    payload = spec.to_dict()
    assert json.loads(json.dumps(payload)) == payload
    restored = DocumentSpec.from_dict(payload)
    assert restored.to_dict() == payload
    assert restored == spec or restored.to_dict() == spec.to_dict()


def test_spec_from_dict_rejects_unknown_keys() -> None:
    with pytest.raises(ConfigurationError, match="unknown key"):
        DocumentSpec.from_dict({"dialect": "gfm", "nope": 1})


def test_spec_from_dict_rejects_wrong_types() -> None:
    with pytest.raises(ConfigurationError, match="seed"):
        DocumentSpec.from_dict({"seed": "fast"})
    with pytest.raises(ConfigurationError, match="include"):
        DocumentSpec.from_dict({"include": "heading.*"})
    with pytest.raises(ConfigurationError, match="elements"):
        DocumentSpec.from_dict({"elements": []})


def test_options_mapping_drives_generation() -> None:
    spec = DocumentSpec(
        seed=1,
        include=["heading.atx.h2", "heading.setext.h2"],
        heading_skeleton=False,
        length=LengthSpec(300),
        elements={
            "heading": ElementRule(
                options={"style": "setext", "levels": [2], "attribute_ratio": 0.0}
            )
        },
    )
    text = Generator(spec).generate()
    assert "\n---" in text


def test_options_mapping_rejects_unknown_field() -> None:
    spec = DocumentSpec(
        seed=1,
        include=["heading.atx.h2"],
        length=LengthSpec(100),
        elements={"heading": ElementRule(options={"nope": 1})},
    )
    with pytest.raises(ConfigurationError, match="unknown option"):
        Generator(spec).generate()


def test_option_types_cover_generator_families() -> None:
    families = {generator.family for generator in build_generators().values()}
    assert set(OPTION_TYPES) | {"html"} == families


@pytest.mark.parametrize("family", sorted(OPTION_TYPES))
def test_every_option_type_builds_from_empty_mapping(family: str) -> None:
    instance: object = build_options(OPTION_TYPES[family], {}, family)
    assert isinstance(instance, OPTION_TYPES[family])


def test_build_options_unknown_key_mentions_valid_names() -> None:
    with pytest.raises(ConfigurationError, match="valid options"):
        build_options(HeadingOptions, {"bogus": True})


# --------------------------------------------------------------------------
# line endings and layout controls
# --------------------------------------------------------------------------


def test_crlf_output_has_no_bare_newlines() -> None:
    text = dummy_md.generate(length=400, seed=2, line_ending="crlf")
    assert "\r\n" in text
    assert "\n" not in text.replace("\r\n", "")


def test_crlf_exact_length() -> None:
    text = dummy_md.generate(length=300, mode="exact", seed=3, line_ending="crlf")
    assert len(text) == 302  # 300 content characters + CRLF terminator
    assert measure_text(text, "chars") == 300
    assert "\r\n" in text


def test_no_trailing_newline() -> None:
    text = dummy_md.generate(length=200, seed=4, trailing_newline=False)
    assert not text.endswith("\n")


def test_no_trailing_newline_exact_chars() -> None:
    text = dummy_md.generate(length=250, mode="exact", seed=4, trailing_newline=False)
    assert len(text) == 250


def test_chunk_parity_with_crlf() -> None:
    whole = dummy_md.generate(length=3000, seed=6, line_ending="crlf")
    streamed = "".join(dummy_md.iter_chunks(length=3000, seed=6, line_ending="crlf"))
    assert streamed == whole


def test_section_chars_controls_chunking() -> None:
    chunks = list(dummy_md.iter_chunks(length=4500, seed=1, section_chars=1000))
    assert len(chunks) > 3
    assert "".join(chunks) == dummy_md.generate(length=4500, seed=1, section_chars=1000)


def test_invalid_layout_values_rejected() -> None:
    with pytest.raises(ConfigurationError, match="section_chars"):
        DocumentSpec(section_chars=10)
    with pytest.raises(ConfigurationError, match="fill_ratio"):
        DocumentSpec(fill_ratio=0)
    with pytest.raises(ConfigurationError, match="line ending"):
        DocumentSpec(line_ending="cr")  # type: ignore[arg-type]


def test_text_seed_is_independent_but_deterministic() -> None:
    first = dummy_md.generate(length=600, seed=10, text_seed=99)
    same = dummy_md.generate(length=600, seed=10, text_seed=99)
    other = dummy_md.generate(length=600, seed=10, text_seed=100)
    assert first == same
    assert first != other


# --------------------------------------------------------------------------
# element options actually take effect
# --------------------------------------------------------------------------


def test_heading_options_setext() -> None:
    context = build_context(
        include=("heading.atx.h2", "heading.setext.h2"),
        options={
            "heading": ElementRule(
                options=HeadingOptions(style="setext", levels=(2,), attribute_ratio=0.0)
            )
        },
    )
    block = REGISTRY.generator("heading").generate(context)
    assert getattr(block, "style", "") == "setext"


def test_paragraph_options_control_length() -> None:
    context = build_context(
        include=("inline.emphasis.asterisk",),
        options={
            "paragraph": ElementRule(
                options=ParagraphOptions(
                    min_sentences=1,
                    max_sentences=1,
                    sentence_min_words=2,
                    sentence_max_words=2,
                    inline_ratio=0.0,
                    emoji_ratio=0.0,
                )
            )
        },
    )
    block = REGISTRY.generator("paragraph").generate(context)
    assert count_words(Document(children=(block,))) <= 3


def test_list_options_control_item_count() -> None:
    context = build_context(
        include=("list.unordered.hyphen",),
        options={"list": ElementRule(options=ListOptions(min_items=3, max_items=3))},
    )
    block = REGISTRY.generator("list").generate(context)
    assert isinstance(block, ListBlock)
    assert len(block.items) == 3


def test_table_options_control_shape() -> None:
    context = build_context(
        include=("table.pipe", "table.align.left"),
        options={
            "table": ElementRule(
                options=TableOptions(
                    min_rows=2,
                    max_rows=2,
                    min_columns=2,
                    max_columns=2,
                    header_only_ratio=0.0,
                )
            )
        },
    )
    block = REGISTRY.generator("table").generate(context)
    assert isinstance(block, Table)
    assert len(block.header) == 2
    assert len(block.rows) == 2


def test_code_options_force_indented() -> None:
    context = build_context(
        include=("code.indented",),
        options={"code": ElementRule(options=CodeOptions(indented_ratio=1.0))},
    )
    block = REGISTRY.generator("code").generate(context)
    assert isinstance(block, CodeBlock)
    assert block.indented


def test_link_options_control_count() -> None:
    context = build_context(
        include=("link.inline",),
        options={"link": ElementRule(options=LinkOptions(min_links=1, max_links=1))},
    )
    block = REGISTRY.generator("link").generate(context)
    assert isinstance(block, Paragraph)
    links = [child for child in block.children if type(child).__name__ == "Link"]
    assert len(links) == 1


def test_math_options_force_delimiter() -> None:
    context = build_context(
        dialect="extended",
        include=("math.display.bracket",),
        options={
            "math": ElementRule(
                options=MathOptions(
                    delimiter="bracket", environment_ratio=0.0, fence_ratio=0.0
                )
            )
        },
    )
    block = REGISTRY.generator("math").generate(context)
    assert isinstance(block, MathBlock)
    assert block.delimiter == "bracket"


def test_diagram_options_set_info_string() -> None:
    context = build_context(
        dialect="extended",
        include=("diagram.mermaid.flowchart",),
        options={
            "diagram": ElementRule(options=DiagramOptions(fence_info="mermaid-v2"))
        },
    )
    block = REGISTRY.generator("diagram").generate(context)
    assert isinstance(block, CodeBlock)
    assert block.info == "mermaid-v2"


def test_thematic_break_options_control_spacing() -> None:
    context = build_context(
        include=("thematic_break.hyphen",),
        options={
            "thematic_break": ElementRule(options=ThematicBreakOptions(spacings=(2,)))
        },
    )
    block = REGISTRY.generator("thematic_break").generate(context)
    assert isinstance(block, ThematicBreak)
    assert block.spacing == 2


def test_frontmatter_options_limit_fields() -> None:
    context = build_context(
        dialect="extended",
        include=("frontmatter.yaml", "meta.title", "meta.tags", "meta.author"),
        options={"frontmatter": ElementRule(options=FrontMatterOptions(max_fields=1))},
    )
    block = REGISTRY.generator("frontmatter").generate(context)
    assert isinstance(block, FrontMatter)
    assert block.content.count("\n") == 0


def test_callout_nested_option_disables_nesting() -> None:
    from dummy_md.elements import QuoteOptions

    context = build_context(
        dialect="extended",
        include=("callout.github.note", "callout.nested"),
        options={
            "callout": ElementRule(options=QuoteOptions(nested_callout_ratio=0.0))
        },
    )
    for _ in range(10):
        block = REGISTRY.generator("callout").generate(context)
        assert isinstance(block, Callout)
        assert not any(isinstance(child, Callout) for child in block.children)


# --------------------------------------------------------------------------
# API and CLI surface
# --------------------------------------------------------------------------


def test_generate_accepts_weights_and_line_endings() -> None:
    text = dummy_md.generate(
        length=500,
        seed=2,
        feature_weights={"inline.code_span": 2.0},
        line_ending="crlf",
        trailing_newline=False,
    )
    assert "\r\n" in text
    assert not text.endswith("\n")


def test_cli_spec_command_round_trips(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["spec", "--chars", "600", "--seed", "5", "--line-ending", "crlf"]) == 0
    payload = json.loads(capsys.readouterr().out)
    spec = DocumentSpec.from_dict(payload)
    assert spec.length.value == 600
    assert spec.line_ending == "crlf"

    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = main(["generate", "--spec", str(spec_file)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == Generator(spec).generate()


def test_cli_feature_weight_flag() -> None:
    assert parse_weights(["table.pipe=3", "inline.code_span=0.5"]) == {
        "table.pipe": 3.0,
        "inline.code_span": 0.5,
    }
    with pytest.raises(dummy_md.DummyMdError):
        parse_weights(["table.pipe"])
    with pytest.raises(dummy_md.DummyMdError):
        parse_weights(["table.pipe=0"])


def test_cli_rejects_unknown_spec_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec_file = tmp_path / "bad.json"
    spec_file.write_text('{"dialect": "gfm", "bogus": 1}', encoding="utf-8")
    assert main(["generate", "--spec", str(spec_file)]) == 1
    assert "unknown key" in capsys.readouterr().err


def test_available_elements_accepts_custom_registry() -> None:
    registry = new_registry()
    registry.add_dialect(
        "tiny", base="gfm", remove=["table.pipe", "code.fenced.backtick"]
    )
    features = dummy_md.available_elements("tiny", registry=registry)
    assert "table.pipe" not in features
    assert "heading.atx.h1" in features
    assert "tiny" in dummy_md.available_dialects(registry=registry)


def test_line_ending_type_export() -> None:
    value: LineEnding = "lf"
    assert value in {"lf", "crlf"}


# --------------------------------------------------------------------------
# custom text styles, presets and spec files
# --------------------------------------------------------------------------


@pytest.fixture
def restore_globals() -> Iterator[None]:
    styles = dict(TEXT_PROVIDERS)
    presets = dict(PRESETS)
    yield
    TEXT_PROVIDERS.clear()
    TEXT_PROVIDERS.update(styles)
    PRESETS.clear()
    PRESETS.update(presets)


class HelloProvider:
    """A deliberately trivial provider to prove the plug-in seam works."""

    name = "hello"

    def word(self, rng: Random) -> str:
        return "hello"


def test_custom_text_style(restore_globals: None) -> None:
    register_text_style("hello", HelloProvider())
    assert "hello" in dummy_md.text_styles()
    spec = DocumentSpec(
        seed=1,
        text_style="hello",
        include=["paragraph.single_line", "heading.atx.h2"],
        heading_skeleton=False,
        length=LengthSpec(300),
    )
    text = Generator(spec).generate()
    assert "hello" in text.lower()


def test_duplicate_text_style_requires_replace(restore_globals: None) -> None:
    with pytest.raises(ConfigurationError, match="already registered"):
        register_text_style("lorem", HelloProvider())
    register_text_style("lorem", HelloProvider(), replace=True)


def test_text_provider_must_match_protocol(restore_globals: None) -> None:
    with pytest.raises(ConfigurationError, match="must define"):
        register_text_style("broken", object())  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError, match="must not be empty"):
        register_text_style("", HelloProvider())


def test_unknown_text_style_names_the_valid_set() -> None:
    with pytest.raises(ConfigurationError, match="unknown text style"):
        DocumentSpec(text_style="nope")


def test_custom_preset(restore_globals: None) -> None:
    preset = Preset(
        name="headings-only",
        description="Only headings, for navigation fixtures",
        include=("heading.*",),
        text_style="lorem",
    )
    register_preset(preset)
    assert "headings-only" in dummy_md.available_presets()
    text = dummy_md.generate(length=400, seed=1, preset="headings-only")
    assert text.startswith("#")
    with pytest.raises(ConfigurationError, match="already registered"):
        register_preset(preset)
    register_preset(Preset(name="headings-only", description="replaced"), replace=True)
    assert dummy_md.available_presets()["headings-only"] == "replaced"


def test_unknown_preset_lists_choices() -> None:
    with pytest.raises(ConfigurationError, match="unknown preset"):
        dummy_md.generate(length=100, preset="nope")


def test_spec_json_round_trip(tmp_path: Path) -> None:
    spec = sample_spec()
    text = spec.to_json()
    assert DocumentSpec.from_json(text).to_dict() == spec.to_dict()

    path = tmp_path / "spec.json"
    same = spec.to_json(path)
    assert path.read_text(encoding="utf-8") == same + "\n"
    assert DocumentSpec.from_json_file(path).to_dict() == spec.to_dict()


def test_spec_json_rejects_bad_input(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="invalid spec JSON"):
        DocumentSpec.from_json("{not json")
    with pytest.raises(ConfigurationError, match="must be an object"):
        DocumentSpec.from_json("[]")
    with pytest.raises(ConfigurationError, match="cannot read spec file"):
        DocumentSpec.from_json_file(tmp_path / "missing.json")
