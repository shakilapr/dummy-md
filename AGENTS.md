# Agent Coding Guidelines for `dummy-md`

This document defines the architectural rules, coding standards, and operational guidelines for AI coding agents and human contributors working within the `dummy-md` repository.

---

## 1. Architectural Prime Directives

Every contribution must strictly adhere to these core invariants:

### 1.1 AST-First Construction
> **NEVER generate raw Markdown strings in an Element Generator.**

- All generators produce typed `MarkdownNode` instances (e.g., `Paragraph`, `Heading`, `Table`, `CodeBlock`).
- The serialization of characters, delimiter escaping, fence delimiters, list indentation, and pipe alignment belongs **exclusively** to the `Renderer` layer (`dummy_md.renderers`).

### 1.2 Strict Determinism
> **NEVER use the global `random` module or unseeded system sources.**

- All random selections, text sampling, counts, and structural choices must use the `context.rng` instance (`random.Random(seed)`).
- Two calls with the same configuration and seed must produce **byte-identical** output across all operating systems and Python versions.

### 1.3 Safe Length Adjustment
> **NEVER slice or truncate serialized Markdown strings to satisfy length budgets.**

- Slicing raw Markdown risks leaving unclosed code fences, broken links, or severed table pipes.
- Length adjustments must expand or trim text within designated **elastic nodes** (such as body paragraphs or list items) before final AST rendering.

### 1.4 Zero Runtime Dependencies for Core
> **The core library must depend solely on the Python Standard Library.**

- Third-party packages (such as `markdown-it-py`, `hypothesis`, `pytest`, and `ruff`) are strictly developer and testing dependencies specified under `[project.optional-dependencies]`.

---

## 2. Repository Layout

```text
dummy-md/
├── ARCHITECTURE.md          # Full architectural specification (no phase details)
├── work-plan.md             # Implementation roadmap and phase deliverables
├── AGENTS.md                # This operational guide for agents
├── README.md                # User-facing library documentation
├── pyproject.toml           # Hatchling packaging and tool configurations
├── .gitignore               # Python and workspace ignore rules
├── src/
│   └── dummy_md/
│       ├── __init__.py      # Top-level API exports
│       ├── api.py           # Simple functional API (generate, iter_chunks, write)
│       ├── config.py        # DocumentSpec, ElementRule, LengthSpec dataclasses
│       ├── exceptions.py    # Library exception classes
│       ├── cli.py           # Command line interface
│       │
│       ├── core/            # Engine orchestration
│       │   ├── nodes.py     # Typed AST nodes (BlockNode, InlineNode, etc.)
│       │   ├── context.py   # GenerationContext and state tracking
│       │   ├── budget.py    # Length units, calculations, and budget ledger
│       │   ├── planner.py   # Constraint-first document planner
│       │   ├── engine.py    # Main Generator orchestrator
│       │   └── registry.py  # Element and Renderer plugin registry
│       │
│       ├── text/            # Content generation (decoupled from syntax)
│       │   ├── base.py      # Base text generator protocols
│       │   ├── pseudowords.py # Syllable-based artificial words
│       │   ├── lorem.py     # Classic Latin Lorem Ipsum
│       │   └── tokens.py    # Stress-testing tokens and alphanumeric IDs
│       │
│       ├── elements/        # Concrete AST element generators
│       │   ├── headings.py
│       │   ├── paragraphs.py
│       │   ├── lists.py
│       │   ├── tables.py
│       │   ├── code.py
│       │   ├── links.py
│       │   ├── images.py
│       │   └── quotes.py
│       │
│       ├── renderers/       # AST to Markdown text serializers
│       │   ├── base.py      # Base renderer & escaping utilities
│       │   ├── commonmark.py# Strict CommonMark renderer
│       │   └── gfm.py       # GitHub Flavored Markdown renderer
│       │
│       ├── extensions/      # Non-core syntax extensions
│       │   ├── footnotes.py
│       │   ├── math.py
│       │   ├── mermaid.py
│       │   └── frontmatter.py
│       │
│       └── presets/         # Predefined generation templates
│           ├── default.py
│           ├── readme.py
│           └── tables.py
│
└── tests/                   # Test suite
    ├── test_elements.py     # AST node and generator unit tests
    ├── test_length.py       # Length budgeting and tolerance tests
    ├── test_renderers.py    # Serializer and parser verification tests
    ├── test_determinism.py  # Seed stability tests
    └── test_cli.py          # Command line behavior tests
```

---

## 3. Step-by-Step: Adding a New Markdown Element

When implementing or extending a Markdown element, follow this exact workflow:

1. **AST Node:** If not already present in `dummy_md.core.nodes`, define the typed dataclass inheriting from `BlockNode` or `InlineNode`.
2. **Options Schema:** Define an immutable `@dataclass(frozen=True)` in `dummy_md.elements.<family>` holding configurable knobs (with sensible defaults).
3. **Element Generator:** Implement the `ElementGenerator` protocol:
   - Accept `(context: GenerationContext, options: CustomOptions)`.
   - Retrieve words or phrases via `context.text_engine`.
   - Use `context.rng` for all random decisions.
   - Return the constructed AST node.
4. **Renderer Implementation:** Add the node formatting logic in `dummy_md.renderers.gfm` (and `commonmark` if applicable):
   - Escape literal markdown characters where required.
   - Format required spacing and newline boundaries.
5. **Registration:** Register the element generator in `dummy_md.core.registry.registry`.
6. **Tests:**
   - Unit test the generator in `tests/test_elements.py`.
   - Add parser verification test using `markdown-it-py` to ensure output parses into the expected semantic tokens.

---

## 4. Coding Standards & Conventions

- **Python Version:** Python 3.10+ required. Use modern type syntax (`list[str]`, `str | None`, `tuple[int, ...]`).
- **Strict Typing:** All public methods, AST nodes, and internal functions must be 100% type-annotated. Code must pass `mypy --strict`.
- **Data Modeling:** Prefer `@dataclass(frozen=True)` for specifications, options, and immutable AST nodes.
- **Error Handling:** Always raise custom exceptions from `dummy_md.exceptions` (`BudgetError`, `ConfigurationError`, `DialectError`).
- **Code Style:** Formatted and linted with `ruff`. Target 88 characters line length.

---

## 5. Development & Testing Commands

Agents must verify changes using the following commands:

```bash
# Run the test suite
pytest

# Run tests with coverage
pytest --cov=dummy_md

# Run type check (strict)
mypy src/dummy_md tests

# Run linter checks
ruff check .

# Run auto-formatter
ruff format .
```

---

## 6. Commit Message Guidelines

Use conventional commits:
- `feat(ast): add Table and TableRow nodes`
- `feat(planner): implement weighted element distribution`
- `fix(renderers): escape pipe characters in table cells`
- `test(determinism): add seed invariance regression tests`
- `docs: update architecture with dialect matrix`
