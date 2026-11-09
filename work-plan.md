# `dummy-md` — Implementation Work Plan

Companion to [`ARCHITECTURE.md`](ARCHITECTURE.md). The design is fixed; this file tracks what is
built and verified. Feature ids refer to the machine-readable catalog in
`src/dummy_md/core/catalog.py`.

Legend: `[x]` implemented and tested · `[ ]` planned · `[-]` deliberately out of scope for now.

**Status:** 423 catalogued targets, 297 implemented (129 CommonMark, 163 GFM, 297 extended).
359 tests, `mypy --strict` clean, `ruff` clean.

---

## Milestone map

| Milestone | Exit criterion | Status |
| :-- | :-- | :-- |
| M0 Foundations | Catalog validates; AST traversal correct | done |
| M1 Core rendering | Every P0 node renders; `markdown-it-py` parses output | done |
| M2 Generation | `generate(length=...)` yields deterministic, valid documents | done |
| M3 Length control | Exact `chars`/`words` hit or `BudgetError` raised | done |
| M4 Public surface | API, presets, CLI, streaming | done |
| M5 Extended dialects | Extended features gated by dialect | done for 6 families |
| M6 Customization | Dialects, renderers, text styles, presets, weights, JSON specs | done |
| M7 Fidelity audit | Every implemented feature reachable and rendered | done |
| M8 Syntax expansion | Pandoc, CriticMarkup, wiki links, more tables/diagrams/HTML | done |

---

## M0 — Foundations `[x]`

- [x] `exceptions`: `DummyMdError`, `ConfigurationError`, `DialectError`, `BudgetError`,
      `RenderError`.
- [x] `core.nodes`: immutable block/inline dataclasses, `Document`, traversal, text extraction.
- [x] `core.features`: `FeatureSpec`, glob matching, capability resolution, requires closure.
- [x] `core.catalog`: full research inventory as data, `implemented` flags.
- [x] `core.dialects`: capability sets derived from the catalog.
- [x] `core.registry`: generator/feature/payload/dialect registration with conflict checks.

## M1 — Core rendering `[x]`

- [x] `renderers.base`: mode-aware escaping, fence and code-span delimiter selection, definition
      rendering, capability guard.
- [x] `renderers.commonmark`: all block and inline formatters.
- [x] `renderers.gfm`: pipe tables with alignment-aware padding and caption support.
- [x] Round-trip tests per node type; generated documents parse with `markdown-it-py`.

## M2 — Generation `[x]`

- [x] `text`: lorem, pseudowords, tokens, alphanumeric, exact-length filler; semantic engine.
- [x] `elements`: headings, paragraphs, thematic breaks, lists, tables, code, links, images,
      HTML, quotes, callouts, footnotes, math, diagrams, front matter (15 generators).
- [x] `core.context`: RNG, depth, heading tracker, reference registry.
- [x] `core.planner`: constraint-first schedule, heading skeleton, variety bias.
- [x] `core.engine`: section assembly, trimming, fit, definition closure.

## M3 — Length control `[x]`

- [x] Units: `chars`, `words`, `lines`, `blocks`, `bytes`.
- [x] Approximate mode with tolerance; exact mode with elastic-operation ladder.
- [x] `BudgetError` carries requested vs. achievable values.
- [x] Determinism across subprocesses with different `PYTHONHASHSEED`.

## M4 — Public surface `[x]`

- [x] `config`: `DocumentSpec`, `ElementRule`, `LengthSpec`, validated.
- [x] `api`: `generate`, `iter_chunks`, `write`, `available_*`, `validate`.
- [x] `presets`: `default`, `minimal`, `readme`, `tables`, `stress`.
- [x] `cli`: `generate`, `spec`, `elements`, `dialects`, `presets`, `validate`.

## M5 — Extended features `[x]`

- [x] Heading and code-fence attributes.
- [x] Figure captions and image size attributes.
- [x] Footnotes: reference plus definition closure, multiline bodies.
- [x] Math: inline/display delimiters, LaTeX environments, payload families.
- [x] Callouts: GitHub alerts and Obsidian kinds, foldable/nested variants.
- [x] Diagrams: nine Mermaid diagram families as fenced blocks.
- [x] Front matter: YAML, TOML, JSON with metadata schemas.
- [ ] Stress fixtures: escapes, Unicode scripts, CRLF, adjacent delimiters (catalogued, not yet
      selectable).

## M6 — Customization `[x]`

- [x] Derived dialects: `registry.add_dialect(name, base=..., add=..., remove=...)`.
- [x] Renderer plug-ins: `registry.register_renderer(name, RendererType)`.
- [x] Text styles: `register_text_style(name, provider)` with built-ins `pseudowords`,
      `lorem`, `tokens`.
- [x] Presets: `register_preset(Preset(...))`, selectable through `generate(preset=...)`.
- [x] Feature weights: `DocumentSpec.feature_weights`, `--feature-weight ID=W`.
- [x] Per-family option dataclasses with mapping (JSON) support and strict validation.
- [x] Layout controls: `line_ending`, `trailing_newline`, `section_chars`, `fill_ratio`,
      `text_seed`, `max_nesting_depth`, `heading_skeleton`, `include_frontmatter`.
- [x] JSON specs: `DocumentSpec.to_json` / `from_json` / `from_json_file`, CLI `spec` and
      `--spec`.
- [x] CLI flags for every knob: `--option`, `--element-weight`, `--min-count`,
      `--feature-weight`, `--line-ending`, `--no-heading-skeleton`, `--no-frontmatter`.
- [x] 76 customization tests covering every seam, every option family and CLI flag errors.
- [x] 22 fidelity tests proving implemented features reach rendered output.

## M7 — Fidelity audit `[x]`

Every feature marked `implemented` must be reachable from generator code and must appear in
rendered output. The audit found and fixed:

- Inline math (`math.inline.dollar`, `math.inline.paren`) had no emitter; paragraphs now build
  `Math` nodes, and the renderer guard checks the delimiter that is actually emitted.
- Inline footnotes (`footnote.inline`) had no emitter; added an `InlineFootnote` node and
  `^[text]` rendering.
- `code.in_blockquote`, `code.in_list` and `list.in_blockquote` were owned by generators that
  never produced those nestings; the catalog now points them at the quoting/listing generator
  that does.
- `blockquote.lazy` had no implementation; `Blockquote` carries a `lazy` flag and the renderer
  emits unprefixed continuation lines.
- `heading.levels.skipped` never allowed a skip; the feature now feeds the heading tracker.
- `table.cell.escaped_pipe`, `table.columns.many` and `table.payload.numeric` were ignored;
  each now gates its construct and numeric cells no longer leak without the feature.
- `FootnoteOptions.multiline_ratio`, `QuoteOptions.nested_ratio`,
  `QuoteOptions.extra_block_ratio` were dead knobs; they are honoured now.
- `FrontMatterOptions.include_ratio` and the unused payload-registry API were removed.
- Renderer guards were corrected for callout kinds, task lists, LaTeX environments and
  code-vs-heading attributes; setext headings place attributes before the underline.
- A static test asserts every implemented feature id is referenced by generator or renderer
  code, so a feature cannot be declared implemented again without a code path.

---

## M8 — Syntax expansion `[x]`

Added the missing core and Pandoc-style syntax that the existing AST could express:

- Inline: superscript, subscript, underline, highlight, insert, small caps, emoji shortcodes,
  CriticMarkup (deletion/insertion/replacement/highlight/comment), abbreviation definitions
  and references.
- Blocks: Pandoc line blocks, fenced divs, theorem blocks, definition lists.
- Lists: alphabetical, Roman-numeral and numbered example lists.
- Links: wiki links (basic, aliases, heading and block targets), Pandoc link attributes.
- Tables: Pandoc simple and multiline styles, plus figure labels.
- Math: equation labels, LaTeX macros, cross-references.
- HTML: SVG, `<img>`, `<picture>`, `<audio>`, `<video>`, `<iframe>`, `<colgroup>`, table parts,
  row/column spans, and markdown-in-HTML containers.
- Diagrams: 21 further Mermaid families plus Graphviz, PlantUML and D2 fence engines.

88 fidelity tests assert each new construct reaches rendered output.

## Next up

1. **Grid tables** — needs a dedicated layout pass for row/column spans; `table.simple` and
   `table.multiline` already cover span-free tables.
2. **Code-block extras** — Docusaurus titles/highlights, line numbers, PyMdown annotations,
   Quarto executable chunks and GitLab JSON tables need extra `CodeBlock` fields.
3. **Citations** — bracketed/narrative/locator forms plus bibliography fixtures.
4. **Platform families** — Obsidian properties/embeds, GitLab references/includes, MyST/MkDocs/
   Quarto directives; each needs a parser to verify output before it is marked implemented.
5. **Stress fixtures** — the 30 `stress.*` rows need raw-byte emission (escapes, CRLF, tabs,
   zero-width characters) instead of the normal escaping path.
6. **MDX** — JSX/expressions require a dedicated dialect and renderer.
7. **CLI streaming for byte targets** — `--size` streams sections but does not precompute
   section counts from bytes.

---

## Out of scope (catalogued only)

- `[-]` MDX/JSX emission: needs a JS-aware renderer and JSX validation.
- `[-]` Executable chunks (Quarto, MyST): content is generated, execution never attempted.
- `[-]` Obsidian properties and GitLab-only macros: no parser to verify them.
- `[-]` Citations and bibliography fixtures: require a multi-file corpus model.

---

## Risks

| Risk | Impact | Mitigation |
| :-- | :-- | :-- |
| Fit loop oscillation | High | Monotonic operation ladder, bounded steps, `BudgetError` diagnostics |
| Escaping divergence by context | High | One mode-aware escape function, golden per-mode tests |
| Dialect claims outrunning reality | High | `implemented` flag, capability guard, per-feature render/parse test |
| Oversized structural blocks | Medium | Size-decayed list nesting, section trimming, structural floors |
| Seed drift across versions | Medium | No `hash()`, stable random ordering, subprocess determinism tests |