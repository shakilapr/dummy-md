# dummy-md

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Types: strict](https://img.shields.io/badge/typing-strict-blueviolet.svg)](https://mypy.readthedocs.io/)

> **Lorem Ipsum for entire Markdown documents, not just paragraphs.**

`dummy-md` generates arbitrary amounts of syntactically valid Markdown as configurable
combinations of Markdown features, filled with placeholder content. It is built for parser
benchmarks, renderer fixtures, editor stress tests, and sample corpora.

Output is produced from a typed AST and serialized per dialect, so tables stay aligned, code
fences close, list nesting indents correctly, and reference links resolve.

- **Dialect-aware:** CommonMark, GFM, and an `extended` dialect (math, footnotes, callouts,
  diagrams, front matter). A feature the dialect cannot express is rejected, never faked.
- **Feature-level selection:** `include` / `exclude` accept exact ids (`table.pipe`) and globs
  (`heading.*`, `math.*`).
- **Deterministic:** same spec and seed → byte-identical output, independent of
  `PYTHONHASHSEED`.
- **Length control:** target `chars`, `words`, `lines`, `blocks`, or `bytes`, in approximate or
  exact mode.
- **Customizable:** pluggable dialects, renderers, text styles and presets; per-element option
  dataclasses; feature-level weights; JSON specs for reproducible fixtures.
- **Zero runtime dependencies:** the core uses only the standard library.

## Installation

```bash
pip install dummy-md
```

For development extras (`pytest`, `hypothesis`, `markdown-it-py`, `ruff`, `mypy`):

```bash
pip install "dummy-md[dev]"
```

## Quickstart

```python
import dummy_md

markdown = dummy_md.generate(length=5000, unit="chars", seed=42)
print(markdown)
```

Pick exactly what the document should contain:

```python
markdown = dummy_md.generate(
    length=8000,
    dialect="gfm",
    include=["heading.*", "paragraph.*", "table.pipe", "list.*", "code.*"],
    exclude=["html.*"],
    seed=1337,
)
```

Unknown or unimplemented feature ids raise `ConfigurationError`; asking CommonMark for
`table.pipe` raises `DialectError` listing the dialects that support it.

### Advanced specification

```python
from dummy_md import DocumentSpec, ElementRule, Generator, LengthSpec
from dummy_md.elements import HeadingOptions, TableOptions

spec = DocumentSpec(
    dialect="gfm",
    seed=42,
    length=LengthSpec(value=15_000, unit="chars", mode="approximate", tolerance=0.03),
    include=["heading.*", "paragraph.*", "table.*", "code.*", "list.*"],
    elements={
        "heading": ElementRule(
            min_count=3,
            max_count=10,
            weight=3,
            options=HeadingOptions(levels=(1, 2, 3), style="atx"),
        ),
        "paragraph": ElementRule(weight=10),
        "table": ElementRule(
            min_count=2,
            weight=4,
            options=TableOptions(min_rows=4, max_rows=8, min_columns=3, max_columns=5),
        ),
    },
    text_style="pseudowords",
    max_nesting_depth=3,
)

generator = Generator(spec)
markdown = generator.generate()
document = generator.to_ast()  # inspect the tree
generator.write("benchmark_fixture.md")
```

### Streaming

```python
for chunk in dummy_md.iter_chunks(length=200_000, unit="chars", seed=7):
    sink.write(chunk)
```

Documents are generated in sections (16k characters by default); concatenating the chunks
equals `generate()` for the same spec.

## Dialects

| Dialect | Adds |
| :-- | :-- |
| `commonmark` | CommonMark core: ATX/Setext headings, lists, code, quotes, HTML blocks, reference links, entities |
| `gfm` | CommonMark + pipe tables, task lists, strikethrough, bare autolinks |
| `extended` | GFM + heading/code attributes, figure captions, footnotes, math, callouts, Mermaid, front matter |
| `stress` | `extended` capability set with token-style text for parser stress |

Counts: 423 catalogued generation targets, 228 currently implemented (117 CommonMark, 151 GFM,
228 extended).

```bash
dummy-md elements --dialect gfm     # implemented ids for a dialect
dummy-md elements --all             # full catalog, unimplemented ids marked
```

## Length control

| Unit | Measures |
| :-- | :-- |
| `chars` | serialized characters, excluding the final line terminator (`\n` or `\r\n`) |
| `words` | words in textual content, excluding markup |
| `lines` | newline-delimited output lines |
| `blocks` | top-level blocks |
| `bytes` | UTF-8 encoded size |

`mode="approximate"` (default) tolerates `tolerance` (default 5%). `mode="exact"` fits the
target by resizing elastic paragraph text — exactness is guaranteed for `chars` and `words`;
for `lines`, `blocks`, and `bytes` an unreachable target raises `BudgetError` with the closest
achievable value.

```python
dummy_md.generate(length=1234, mode="exact", seed=5)  # exactly 1234 characters
```

## Presets

```python
dummy_md.generate(length=3000, preset="readme", seed=1)
```

`default`, `minimal`, `readme`, `tables`, `stress`. `dummy_md.available_presets()` returns the
descriptions.

Custom presets are registered once and selectable everywhere:

```python
from dummy_md import Preset, register_preset

register_preset(
    Preset(
        name="docs",
        description="Documentation-shaped fixture",
        include=("heading.*", "paragraph.*", "code.*", "list.*"),
        exclude=("html.*",),
        text_style="lorem",
    )
)
dummy_md.generate(length=4000, preset="docs")
```

## Customization

Everything that decides output is addressable without forking the library.

**Element options.** Every generator family owns a frozen options dataclass.

```python
from dummy_md import DocumentSpec, ElementRule
from dummy_md.elements import (
    CodeOptions,
    HeadingOptions,
    ListOptions,
    MathOptions,
    ParagraphOptions,
    TableOptions,
)

spec = DocumentSpec(
    seed=7,
    include=["heading.*", "paragraph.*", "list.*", "table.*", "code.*", "math.*"],
    elements={
        "heading": ElementRule(options=HeadingOptions(levels=(1, 2), style="setext")),
        "paragraph": ElementRule(
            options=ParagraphOptions(min_sentences=2, max_sentences=5, inline_ratio=0.4)
        ),
        "list": ElementRule(options=ListOptions(min_items=2, max_items=6)),
        "table": ElementRule(
            options=TableOptions(min_rows=3, max_rows=8, min_columns=2, max_columns=5)
        ),
        "code": ElementRule(
            options=CodeOptions(indented_ratio=0.0, long_fence_ratio=0.3)
        ),
        "math": ElementRule(options=MathOptions(delimiter="dollar")),
    },
)
```

Options may be dataclasses or plain mappings (the form JSON uses); unknown fields raise
`ConfigurationError` naming the valid ones.

**Feature weights.** Nudge how often individual variants appear.

```python
dummy_md.generate(
    length=10_000,
    seed=99,
    feature_weights={
        "inline.emphasis.asterisk": 3.0,
        "inline.strong.asterisk": 2.0,
        "list.task.checked": 0.5,
        "math.display.dollar": 4.0,
    },
)
```

**Custom dialects and renderers.** Derive a dialect from a built-in one and register it.

```python
from dummy_md import Registry, elements
from dummy_md.renderers import GFMRenderer

registry = Registry()
elements.register(registry)
registry.add_dialect(
    "docs", base="gfm", add=["math.display.dollar"], remove=["html.block"]
)
registry.register_renderer("gfm-strict", GFMRenderer)
registry.add_dialect("strict", base="gfm", renderer="gfm-strict")

markdown = dummy_md.generate(length=2000, dialect="docs", registry=registry)
```

**Custom text styles.** Supply your own word source; sentence structure, casing and punctuation
are handled by the content engine.

```python
from random import Random

from dummy_md import register_text_style


class WordList:
    name = "words"
    WORDS = ("alpha", "bravo", "charlie", "delta")

    def word(self, rng: Random) -> str:
        return rng.choice(self.WORDS)


register_text_style("words", WordList())
dummy_md.generate(length=1200, text_style="words")
```

**Layout controls.** `line_ending="crlf"`, `trailing_newline=False`, `section_chars=...`,
`fill_ratio=...`, `text_seed=...`, `max_nesting_depth=...`, plus `heading_skeleton` and
`include_frontmatter` switches are all part of `DocumentSpec`.

**JSON specs.** Persist a run and reproduce it exactly.

```python
from dummy_md import DocumentSpec

spec = DocumentSpec(seed=5, include=("table.*",), length=dummy_md.LengthSpec(2000))
spec.to_json("fixture-spec.json")  # also returns the JSON text
same = DocumentSpec.from_json_file("fixture-spec.json")
assert same.to_dict() == spec.to_dict()
```

```bash
dummy-md spec --chars 5000 --seed 42 > spec.json
dummy-md generate --spec spec.json
```

## Command line

```bash
dummy-md generate --chars 10000 --dialect gfm --seed 42
dummy-md generate --words 2500 --preset tables -o tables.md
dummy-md generate --bytes 2MB --exclude "html.*" --seed 1337
dummy-md generate --chars 4000 --feature-weight "list.task.checked=3" --line-ending crlf
dummy-md generate --chars 6000 --option heading.style=setext --element-weight table=3
dummy-md generate --chars 6000 --min-count paragraph=4 --no-heading-skeleton --no-frontmatter
dummy-md spec --chars 5000 --seed 42 > spec.json
dummy-md generate --spec spec.json -o fixture.md
dummy-md elements --dialect extended
dummy-md dialects
dummy-md presets
dummy-md validate fixture.md --dialect gfm
```

Exit codes: `0` success, `1` generation/validation failure, `2` usage error. Errors go to
stderr. `validate` needs the `[dev]` extra (it uses `markdown-it-py`).

## Determinism

```python
import hashlib

first = dummy_md.generate(length=2000, seed=4242)
second = dummy_md.generate(length=2000, seed=4242)
assert (
    hashlib.sha256(first.encode()).digest() == hashlib.sha256(second.encode()).digest()
)
```

All randomness flows through one seeded `random.Random`; nothing reads the clock, environment,
or hash order.

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # POSIX: .venv/bin/pip
.venv/Scripts/python -m pytest
.venv/Scripts/python -m mypy src/dummy_md tests
.venv/Scripts/python -m ruff check .
```

The design is specified in [`ARCHITECTURE.md`](ARCHITECTURE.md); build status is tracked in
[`work-plan.md`](work-plan.md); contributor rules are in [`AGENTS.md`](AGENTS.md).

## License

MIT.