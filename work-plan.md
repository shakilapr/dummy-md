# `dummy-md` — Implementation Work Plan & Roadmap

This document outlines the phased development plan for implementing the `dummy-md` library according to the specifications in [`ARCHITECTURE.md`](file:///e:/work/other/dummy-md/ARCHITECTURE.md).

---

## Roadmap Overview

```mermaid
flowchart LR
    P1["Phase 1: Core MVP\n(AST, Core Elements, Text, GFM Renderer, Simple API)"] --> P2["Phase 2: Advanced Composition\n(Budget Engine, Planner, Nesting, Presets)"]
    P2 --> P3["Phase 3: Full Dialect Coverage\n(Tables, Task Lists, Footnotes, Extensions)"]
    P3 --> P4["Phase 4: Production Quality\n(Streaming, CLI, Property Testing, Packaging)"]
```

| Phase | Milestone | Primary Objective | Key Deliverables |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Core MVP | Functional generator for basic GFM documents | AST, Content Engine, Core Generators, Simple API, Determinism |
| **Phase 2** | Advanced Composition | Accurate length budgeting and structural control | Budget engine, Planner, Constraints, Presets, Nesting |
| **Phase 3** | Full Coverage | Extended Markdown element catalog and dialect support | Tables, Task lists, Footnotes, Math, Mermaid, CommonMark/GFM |
| **Phase 4** | Production Hardening | CLI, streaming scalability, and property validation | Streaming iterator, CLI tool, Hypothesis tests, Packaging |

---

## Phase 1: Core MVP

### Goals
Deliver a functional, tested Python package that can generate valid, deterministic GitHub Flavored Markdown documents using a simple API.

### Scope & Tasks
1. **Repository & Foundation Setup**
   - [ ] Establish package layout under `src/dummy_md/`.
   - [ ] Define exceptions hierarchy (`DummyMdError`, `BudgetError`, `DialectError`, `ConfigurationError`).
   - [ ] Configure linting and type checking (Ruff, Mypy in strict mode).

2. **AST Infrastructure (`dummy_md.core.nodes`)**
   - [ ] Base `MarkdownNode`, `BlockNode`, and `InlineNode` types.
   - [ ] Core nodes: `Document`, `Heading`, `Paragraph`, `Text`, `Emphasis`, `CodeInline`, `CodeBlock`, `ListBlock`, `ListItem`.
   - [ ] Node visitor and traversal utilities.

3. **Dummy Content Engine (`dummy_md.text`)**
   - [ ] `DummyContentEngine` protocol and base class.
   - [ ] `PseudowordsGenerator`: Pronounceable syllables and sentence structure.
   - [ ] `LoremGenerator`: Classic Latin placeholder text.
   - [ ] Context helpers: `heading_phrase()`, `sentence()`, `paragraph()`, `identifier()`.

4. **Core Element Generators (`dummy_md.elements`)**
   - [ ] `HeadingGenerator` (ATX styles, H1–H6).
   - [ ] `ParagraphGenerator` (inline formatting injection: bold, italic, inline code).
   - [ ] `ListGenerator` (unordered and ordered lists).
   - [ ] `CodeBlockGenerator` (basic syntax highlighting tags, backtick fences).

5. **GFM Renderer (`dummy_md.renderers`)**
   - [ ] Renderer base protocol and escaping logic (`markdown_escape`).
   - [ ] Serializer for core AST nodes into valid GFM text with normalized blank lines.

6. **Simple Public API (`dummy_md.api`)**
   - [ ] `dummy_md.generate(length=..., unit=..., dialect="gfm", seed=...)`.
   - [ ] Seeded `random.Random` isolation for 100% reproducibility.

### Acceptance Criteria
- Running `dummy_md.generate(length=1000, seed=42)` returns valid Markdown.
- Output parses cleanly with standard Markdown parsers without structural errors.
- Calling `generate()` with the same seed produces byte-identical strings.
- 100% type annotation coverage passes `mypy --strict`.

---

## Phase 2: Advanced Composition & Budgeting

### Goals
Implement the constraint-first document planner, length budgeting engine, and complex nesting rules.

### Scope & Tasks
1. **Length & Budget Engine (`dummy_md.core.budget`)**
   - [ ] Measurement drivers for `chars`, `words`, `lines`, and `blocks`.
   - [ ] Approximate mode with configurable tolerance (default `±5%`).
   - [ ] Exact mode with feasibility checks and `BudgetError`.
   - [ ] Elastic node post-processing (expanding/contracting filler text).

2. **Document Planner (`dummy_md.core.planner`)**
   - [ ] Constraint solver: guarantee elements with `min_count > 0` are scheduled.
   - [ ] Weighted element selection for remaining budget capacity.
   - [ ] Hierarchy tracking for headings (prevent orphaned H3/H4 tags).
   - [ ] Nesting depth limiter (`max_nesting_depth`).

3. **Advanced AST Nodes & Nesting**
   - [ ] `Blockquote` generator and nested blockquote support.
   - [ ] Nested lists (ordered inside unordered and vice versa).
   - [ ] Reference definitions collector (`[id]: url` at document root).

4. **Advanced API & Configuration (`dummy_md.config`)**
   - [ ] `DocumentSpec`, `ElementRule`, `LengthSpec` dataclasses.
   - [ ] `Generator` class with `generate()`, `to_ast()`, and `write(path)` methods.

5. **Built-in Presets (`dummy_md.presets`)**
   - [ ] `default`: Balanced mix of standard elements.
   - [ ] `readme`: Project overview structure (title, badges, description, code snippets, lists).
   - [ ] `minimal`: Lightweight heading and paragraph sequences.

### Acceptance Criteria
- Documents generated in approximate mode fall within specified tolerance.
- Specifying mandatory element counts (`min_count=3`) guarantees at least 3 occurrences in output.
- Heading progression maintains logical semantic hierarchy.
- Presets produce recognizable, structurally sensible document formats.

---

## Phase 3: Full Dialect Coverage & Extensions

### Goals
Complete the full Markdown feature catalog, support dialect distinction (CommonMark vs. GFM vs. Extended), and implement the plugin registry.

### Scope & Tasks
1. **Tables Generator & GFM Support (`dummy_md.elements.tables`)**
   - [ ] Table AST node: headers, alignment (`left`, `center`, `right`), rows, cells.
   - [ ] GFM pipe table serialization with cell padding and pipe escaping (`\|`).
   - [ ] Table options: `min_rows`, `max_rows`, `min_columns`, `max_columns`, `alignment`.

2. **Task Lists & Strikethrough**
   - [ ] Task list items (`- [ ]`, `- [x]`) with configurable completion ratios.
   - [ ] Strikethrough inline formatting (`~~text~~`).

3. **References & Footnotes (`dummy_md.elements.references`, `dummy_md.extensions.footnotes`)**
   - [ ] Footnote markers (`[^1]`) and corresponding definition blocks at document tail.
   - [ ] Extended reference link generator with collision-free ID hashing.

4. **Extended Elements (`dummy_md.extensions`)**
   - [ ] Math blocks and inline math (`$...$`, `$$...$$`).
   - [ ] Mermaid diagram blocks (`graph TD`, `sequenceDiagram`).
   - [ ] Admonitions / Callouts (`> [!NOTE]`, `> [!WARNING]`).
   - [ ] Frontmatter blocks (YAML `---` and TOML `+++`).

5. **Dialect Matrix & Validator**
   - [ ] Strict CommonMark renderer (disables GFM pipe tables and task lists).
   - [ ] Dialect capability validator (warns or converts unsupported nodes).
   - [ ] Dynamic Element and Renderer Registry (`ElementRegistry`).

### Acceptance Criteria
- All 14 element families from the architectural specification are supported.
- GFM tables render with clean alignment markers and valid pipe delimiters.
- Unsupported elements in CommonMark mode fall back gracefully or report explicit dialect errors.
- Footnote links match their definitions 1:1 without dangling references.

---

## Phase 4: Production Quality, Streaming, CLI & Ecosystem

### Goals
Prepare `dummy-md` for high-performance production usage, large-scale benchmarks, command-line execution, and PyPI distribution.

### Scope & Tasks
1. **Streaming & Large File Scalability**
   - [ ] Implement `Generator.iter_chunks()` yielding incremental sections.
   - [ ] Byte-accurate size targeting (`--size 100MB`) written directly to disk.
   - [ ] Constant memory profile verified under heap profiling for documents > 100MB.

2. **Command Line Interface (`dummy_md.cli`)**
   - [ ] CLI commands using Python standard `argparse`:
     - `dummy-md generate [options]`
     - `dummy-md elements`
     - `dummy-md presets`
     - `dummy-md validate <file.md>`
   - [ ] Clean stderr reporting, shell exit codes, and pipe redirection (`dummy-md generate | head`).

3. **Comprehensive Testing Suite**
   - [ ] Property-based testing with `Hypothesis`:
     - Random seeds and configurations never throw unhandled exceptions.
     - Generated output length conforms to tolerances.
   - [ ] Parser verification suite using `markdown-it-py`:
     - Verify AST fidelity between generated text and parser output tokens.
   - [ ] Determinism regression tests across Python versions.

4. **Plugin Packaging & Documentation**
   - [ ] `dummy_md.elements` entry points discovery for external pip packages.
   - [ ] Complete API documentation, code examples, and performance guidelines.
   - [ ] GitHub Actions CI workflows for linting, testing, and multi-OS matrix builds.

### Acceptance Criteria
- `dummy-md generate --size 50MB --output test.md` completes in acceptable time with < 50MB RAM usage.
- All CLI commands work seamlessly from terminal.
- 95%+ test coverage across unit, property, and integration tests.
- Clean package build (`hatch build` / `pip install .`).

---

## Risk Analysis & Mitigation Strategies

| Risk | Impact | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Length calculation runaway** | High | Medium | Isolate elastic filler adjustments to body paragraphs; pre-calculate fixed structural baselines before generating text. |
| **Parser syntax divergences** | Medium | High | Rely on AST construction; test generated text against strict CommonMark and GFM parsers (`markdown-it-py`). |
| **Memory exhaustion on large files** | High | Low | Emit AST sections incrementally through generator iterators rather than holding multi-gigabyte trees in RAM. |
| **Seed divergence across OSes** | Medium | Low | Use isolated `random.Random` instances with standard algorithms; avoid platform-dependent floats in hashing or selection. |
