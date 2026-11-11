"""Generate showcase documents and reproducible spec files.

``outputs/`` is git-ignored; it is a scratch area for browsing many generated
documents. ``examples/`` holds a small committed selection, each paired with the
JSON spec used to produce it.
"""

from __future__ import annotations

from pathlib import Path

from dummy_md import DocumentSpec, ElementRule, Generator, LengthSpec
from dummy_md.elements import HeadingOptions, ParagraphOptions, TableOptions

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
EXAMPLES = ROOT / "examples"

SPECS: dict[str, DocumentSpec] = {
    "commonmark-showcase": DocumentSpec(
        dialect="commonmark",
        seed=11,
        length=LengthSpec(4000),
        text_style="pseudowords",
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2, 3, 4))),
        },
    ),
    "gfm-showcase": DocumentSpec(
        dialect="gfm",
        seed=12,
        length=LengthSpec(6000),
        elements={
            "table": ElementRule(options=TableOptions(min_rows=3, max_rows=6)),
            "heading": ElementRule(options=HeadingOptions(levels=(2, 3, 4))),
        },
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
    ),
    "extended-showcase": DocumentSpec(
        dialect="extended",
        seed=13,
        length=LengthSpec(8000),
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2, 3, 4))),
        },
    ),
    "stress-showcase": DocumentSpec(
        dialect="stress",
        seed=14,
        length=LengthSpec(6000),
        max_nesting_depth=4,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2, 3, 4))),
        },
    ),
}

FAMILY_SPECS: dict[str, DocumentSpec] = {
    "citations": DocumentSpec(
        dialect="extended",
        seed=21,
        length=LengthSpec(3000),
        include=["citation.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="atx")),
        },
    ),
    "directives": DocumentSpec(
        dialect="extended",
        seed=22,
        length=LengthSpec(4000),
        include=["directive.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="atx")),
        },
    ),
    "platform": DocumentSpec(
        dialect="extended",
        seed=23,
        length=LengthSpec(4000),
        include=["platform.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="atx")),
        },
    ),
    "mdx": DocumentSpec(
        dialect="stress",
        seed=24,
        length=LengthSpec(3000),
        include=["mdx.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="atx")),
        },
    ),
    "grid-tables": DocumentSpec(
        dialect="extended",
        seed=25,
        length=LengthSpec(3000),
        include=["table.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "table": ElementRule(options=TableOptions(min_rows=3, max_rows=5)),
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="atx")),
        },
    ),
    "code-extras": DocumentSpec(
        dialect="extended",
        seed=26,
        length=LengthSpec(3000),
        include=["code.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="atx")),
        },
    ),
    "pandoc-extras": DocumentSpec(
        dialect="extended",
        seed=27,
        length=LengthSpec(3000),
        include=["paragraph.*", "image.*", "math.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "paragraph": ElementRule(options=ParagraphOptions(block_ratio=0.6)),
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="setext")),
        },
    ),
    "stress-text": DocumentSpec(
        dialect="stress",
        seed=28,
        length=LengthSpec(3000),
        include=["stress.*", "heading.*"],
        heading_skeleton=False,
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
        elements={
            "heading": ElementRule(options=HeadingOptions(levels=(2,), style="atx")),
        },
    ),
}

SEED_SPECS = tuple(
    DocumentSpec(
        dialect="extended",
        seed=seed,
        length=LengthSpec(1800),
        exclude=["heading.levels.skipped", "heading.titles.repeated"],
    )
    for seed in range(6)
)


def _with_title(text: str, title: str) -> str:
    heading = f"# {title}\n\n"
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            rest = text[end + 5 :].lstrip("\n")
            return text[: end + 5] + "\n" + heading + rest
    return heading + text.lstrip("\n")


def main() -> None:
    OUTPUTS.mkdir(exist_ok=True)
    EXAMPLES.mkdir(exist_ok=True)
    for name, spec in SPECS.items():
        folder = OUTPUTS / spec.dialect
        folder.mkdir(exist_ok=True)
        (folder / f"{name}.md").write_text(
            Generator(spec).generate(), encoding="utf-8", newline="\n"
        )
    families = OUTPUTS / "families"
    families.mkdir(exist_ok=True)
    for name, spec in FAMILY_SPECS.items():
        title = name.replace("-", " ").title()
        (families / f"{name}.md").write_text(
            _with_title(Generator(spec).generate(), title),
            encoding="utf-8",
            newline="\n",
        )
    seeds = OUTPUTS / "seeds"
    seeds.mkdir(exist_ok=True)
    for index, spec in enumerate(SEED_SPECS):
        (seeds / f"seed-{index:02d}.md").write_text(
            Generator(spec).generate(), encoding="utf-8", newline="\n"
        )
    for name in (
        "commonmark-showcase",
        "gfm-showcase",
        "extended-showcase",
        "stress-showcase",
    ):
        spec = SPECS[name]
        (EXAMPLES / f"{name}.md").write_text(
            Generator(spec).generate(), encoding="utf-8", newline="\n"
        )
        spec.to_json(EXAMPLES / f"{name}.json")


if __name__ == "__main__":
    main()
