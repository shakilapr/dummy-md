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
| `chars` | serialized characters, excluding the trailing newline |
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

## Command line

```bash
dummy-md generate --chars 10000 --dialect gfm --seed 42
dummy-md generate --words 2500 --preset tables -o tables.md
dummy-md generate --bytes 2MB --exclude "html.*" --seed 1337
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