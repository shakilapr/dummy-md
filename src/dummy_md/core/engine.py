"""Engine: resolve features, plan blocks, fit the budget, and emit output."""

from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path
from random import Random

from dummy_md.config import DocumentSpec
from dummy_md.core.budget import BudgetTracker, fit_document, measure, measure_text
from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, Document
from dummy_md.core.planner import Planner
from dummy_md.core.registry import Registry
from dummy_md.core.registry import registry as default_registry
from dummy_md.renderers import get_renderer
from dummy_md.renderers.base import BaseRenderer
from dummy_md.text import TEXT_PROVIDERS, DummyContentEngine

SECTION_CHARS = 16_000
_FILL_TARGET = 0.9


class Generator:
    """Turns a :class:`DocumentSpec` into Markdown text or an AST."""

    def __init__(self, spec: DocumentSpec, registry: Registry | None = None) -> None:
        self.spec = spec
        self.registry = registry if registry is not None else default_registry
        self._ensure_generators()

    # -- setup ------------------------------------------------------------
    def _ensure_generators(self) -> None:
        from dummy_md import elements

        registered = set(self.registry.generator_families())
        for generator in elements.build_generators().values():
            if generator.family not in registered:
                self.registry.register_generator(generator)
        self.registry.validate()

    def _context(self) -> GenerationContext:
        selected = self.registry.resolve(
            dialect=self.spec.dialect,
            include=self.spec.include,
            exclude=self.spec.exclude,
        )
        rng = Random(self.spec.seed)
        return GenerationContext(
            rng=rng,
            dialect=self.registry.dialect(self.spec.dialect),
            text=DummyContentEngine(rng, TEXT_PROVIDERS[self.spec.text_style]),
            active_features=selected,
            budget=BudgetTracker(
                unit=self.spec.length.unit,
                target=self.spec.length.value,
                mode=self.spec.length.mode,
                tolerance=self.spec.length.tolerance,
            ),
            options=self.spec.elements,
            max_depth=self.spec.max_nesting_depth,
        )

    # -- generation -------------------------------------------------------
    def generate(self) -> str:
        return "".join(self.iter_chunks())

    def iter_chunks(self, chunk_size: int | None = None) -> Iterator[str]:
        if self.spec.length.value == 0:
            return
        context = self._context()
        planner = Planner(context, self.registry, self.spec)
        renderer = get_renderer(context.dialect)
        sections = self._section_count(chunk_size)
        remaining = self.spec.length.value
        for index in range(sections):
            remaining_sections = sections - index
            target = max(1, remaining // remaining_sections)
            document = self._build_section(context, planner, index, target, renderer)
            floor = self._floor(planner, len(document.children))
            fitted, text = fit_document(
                document,
                renderer,
                self._tracker(target),
                context,
                floor_blocks=floor,
            )
            remaining = max(0, remaining - self._consumed(fitted, text))
            yield text

    def to_ast(self) -> Document:
        if self.spec.length.value == 0:
            return Document()
        context = self._context()
        planner = Planner(context, self.registry, self.spec)
        renderer = get_renderer(context.dialect)
        sections = self._section_count(None)
        remaining = self.spec.length.value
        children: list[BlockNode] = []
        for index in range(sections):
            remaining_sections = sections - index
            target = max(1, remaining // remaining_sections)
            document = self._build_section(context, planner, index, target, renderer)
            floor = self._floor(planner, len(document.children))
            fitted, text = fit_document(
                document,
                renderer,
                self._tracker(target),
                context,
                floor_blocks=floor,
            )
            children.extend(fitted.children)
            remaining = max(0, remaining - self._consumed(fitted, text))
        return Document(
            children=tuple(children),
            link_definitions=tuple(context.refs.links.values()),
            footnote_definitions=tuple(context.refs.footnotes.values()),
        )

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            for chunk in self.iter_chunks():
                handle.write(chunk)
        return target

    # -- helpers ----------------------------------------------------------
    def _section_count(self, chunk_size: int | None) -> int:
        if self.spec.length.unit not in {"chars", "bytes"}:
            return 1
        size = max(1_000, chunk_size or SECTION_CHARS)
        return max(1, math.ceil(self.spec.length.value / size))

    def _tracker(self, target: int) -> BudgetTracker:
        return BudgetTracker(
            unit=self.spec.length.unit,
            target=target,
            mode=self.spec.length.mode,
            tolerance=self.spec.length.tolerance,
        )

    def _consumed(self, document: Document, text: str) -> int:
        unit = self.spec.length.unit
        if unit in {"chars", "bytes", "lines"}:
            return measure_text(text, unit)
        return measure(document, text, unit)

    def _build_section(
        self,
        context: GenerationContext,
        planner: Planner,
        index: int,
        target: int,
        renderer: BaseRenderer,
    ) -> Document:
        context.block_hint = self._block_hint(target)
        blocks = planner.skeleton(
            section_index=index,
            allow_frontmatter=self._frontmatter_fits(target),
            allow_title=self._title_fits(target),
        )
        skeleton_count = len(blocks)
        while planner.can_continue():
            document = self._assemble(context, blocks)
            if (
                self._document_measure(document, renderer) >= target * _FILL_TARGET
                and not planner.remaining_minimum()
            ):
                break
            block = planner.next_block()
            if block is None:
                break
            blocks.append(block)
        blocks = self._trim(context, blocks, planner, target, renderer, skeleton_count)
        return self._assemble(context, blocks)

    def _assemble(
        self, context: GenerationContext, blocks: list[BlockNode]
    ) -> Document:
        return Document(
            children=tuple(blocks),
            link_definitions=tuple(context.refs.links.values()),
            footnote_definitions=tuple(context.refs.footnotes.values()),
        )

    def _document_measure(self, document: Document, renderer: BaseRenderer) -> int:
        if self.spec.length.unit == "blocks":
            return len(document.children)
        text = renderer.render(document)
        return measure(document, text, self.spec.length.unit)

    def _block_hint(self, target: int) -> int:
        unit = self.spec.length.unit
        if unit in {"chars", "bytes"}:
            return max(60, target)
        if unit == "words":
            return max(60, target * 6)
        return max(60, target * 120)

    def _frontmatter_fits(self, target: int) -> bool:
        unit = self.spec.length.unit
        if unit in {"chars", "bytes"}:
            return target >= 500
        if unit == "words":
            return target >= 80
        return True

    def _title_fits(self, target: int) -> bool:
        unit = self.spec.length.unit
        if unit in {"chars", "bytes"}:
            return target >= 24
        return True

    def _trim(
        self,
        context: GenerationContext,
        blocks: list[BlockNode],
        planner: Planner,
        target: int,
        renderer: BaseRenderer,
        protected_prefix: int,
    ) -> list[BlockNode]:
        """Drop surplus blocks before fitting, never below a min_count rule."""
        minimums = {
            family: planner.rule(family).min_count
            for family in planner.families
            if planner.rule(family).min_count
        }
        counts: dict[str, int] = dict.fromkeys(minimums, 0)
        families = [self._family_of(block) for block in blocks]
        for family in families:
            if family in counts:
                counts[family] += 1
        index = len(blocks) - 1
        while index >= protected_prefix:
            size = self._document_measure(self._assemble(context, blocks), renderer)
            if size <= target:
                break
            family = families[index]
            minimum = minimums.get(family, 0)
            if family in counts and counts[family] <= minimum:
                index -= 1
                continue
            del blocks[index]
            del families[index]
            if family in counts:
                counts[family] -= 1
            index = min(index - 1, len(blocks) - 1)
        return blocks

    @staticmethod
    def _family_of(block: BlockNode) -> str:
        from dummy_md.core.nodes import (
            Blockquote,
            Callout,
            CodeBlock,
            Figure,
            FrontMatter,
            Heading,
            HTMLBlock,
            ListBlock,
            MathBlock,
            Paragraph,
            Table,
            ThematicBreak,
        )

        if isinstance(block, Heading):
            return "heading"
        if isinstance(block, ThematicBreak):
            return "thematic_break"
        if isinstance(block, CodeBlock):
            return "code"
        if isinstance(block, ListBlock):
            return "list"
        if isinstance(block, Table):
            return "table"
        if isinstance(block, Blockquote):
            return "blockquote"
        if isinstance(block, Callout):
            return "callout"
        if isinstance(block, HTMLBlock):
            return "html"
        if isinstance(block, Figure):
            return "image"
        if isinstance(block, MathBlock):
            return "math"
        if isinstance(block, FrontMatter):
            return "frontmatter"
        if isinstance(block, Paragraph):
            return "paragraph"
        return "other"

    @staticmethod
    def _floor(planner: Planner, block_count: int) -> int:
        minimum = sum(
            max(0, planner.rule(family).min_count) for family in planner.families
        )
        return max(1, min(block_count, minimum + 1))
