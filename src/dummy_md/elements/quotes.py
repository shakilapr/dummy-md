"""Blockquote and callout generation."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    BlockNode,
    Blockquote,
    Callout,
    CodeBlock,
    Heading,
    LineBreak,
    ListBlock,
    ListItem,
    Paragraph,
    Text,
)
from dummy_md.elements._util import check_ratio, resolve_options
from dummy_md.elements.paragraphs import ParagraphGenerator
from dummy_md.elements.tables import TableGenerator

_GITHUB_CALLOUTS = {
    "callout.github.note": "note",
    "callout.github.tip": "tip",
    "callout.github.important": "important",
    "callout.github.warning": "warning",
    "callout.github.caution": "caution",
}

_OBSIDIAN_CALLOUTS = {
    "callout.obsidian.note": "note",
    "callout.obsidian.abstract": "abstract",
    "callout.obsidian.info": "info",
    "callout.obsidian.todo": "todo",
    "callout.obsidian.tip": "tip",
    "callout.obsidian.success": "success",
    "callout.obsidian.question": "question",
    "callout.obsidian.warning": "warning",
    "callout.obsidian.failure": "failure",
    "callout.obsidian.danger": "danger",
    "callout.obsidian.bug": "bug",
    "callout.obsidian.example": "example",
    "callout.obsidian.quote": "quote",
}


@dataclass(frozen=True, slots=True)
class QuoteOptions:
    nested_ratio: float = 0.25
    extra_block_ratio: float = 0.2
    title_ratio: float = 0.4
    foldable_ratio: float = 0.3
    nested_callout_ratio: float = 0.2
    lazy_ratio: float = 0.6

    def __post_init__(self) -> None:
        for name in (
            "nested_ratio",
            "extra_block_ratio",
            "title_ratio",
            "foldable_ratio",
            "nested_callout_ratio",
            "lazy_ratio",
        ):
            check_ratio(getattr(self, name), name)


class QuoteGenerator:
    family = "blockquote"

    def __init__(
        self,
        paragraphs: ParagraphGenerator | None = None,
        tables: TableGenerator | None = None,
    ) -> None:
        self._paragraphs = paragraphs or ParagraphGenerator()
        self._tables = tables or TableGenerator()

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, QuoteOptions(), QuoteOptions)
        return self._quote(context, options, depth=0)

    def _quote(
        self,
        context: GenerationContext,
        options: QuoteOptions,
        *,
        depth: int,
    ) -> Blockquote:
        lazy = (
            context.supports("blockquote.lazy")
            and context.rng.random() < options.lazy_ratio
        )
        first = (
            self._lazy_paragraph(context)
            if lazy
            else self._paragraphs.generate(context)
        )
        children: list[BlockNode] = [first]

        if context.supports("blockquote.multi_paragraph"):
            children.append(self._paragraphs.generate(context))

        heading_ok = context.supports("blockquote.heading")
        list_ok = context.supports_any(("blockquote.list", "list.in_blockquote"))
        code_ok = context.supports_any(("blockquote.code", "code.in_blockquote"))
        table_ok = context.supports("blockquote.table")
        nested_ok = (
            context.supports("blockquote.nested") and depth < 2 and context.can_nest
        )

        if heading_ok and context.rng.random() < options.extra_block_ratio:
            children.append(
                Heading(
                    level=context.rng.randint(2, 4),
                    children=(Text(context.text.heading_phrase(2)),),
                )
            )

        if list_ok and context.rng.random() < options.extra_block_ratio:
            children.append(
                ListBlock(
                    items=(
                        ListItem(children=(self._paragraphs.generate(context),)),
                        ListItem(children=(self._paragraphs.generate(context),)),
                    )
                )
            )

        if code_ok and context.rng.random() < options.extra_block_ratio:
            children.append(CodeBlock(code=context.text.sentence(), info="text"))

        if table_ok and context.rng.random() < options.extra_block_ratio:
            children.append(self._tables.generate(context))

        if nested_ok and context.rng.random() < options.nested_ratio:
            children.append(self._quote(context.nested(), options, depth=depth + 1))

        return Blockquote(children=tuple(children), lazy=lazy)

    @staticmethod
    def _lazy_paragraph(context: GenerationContext) -> Paragraph:
        return Paragraph(
            children=(
                Text(context.text.sentence()),
                LineBreak(hard=False, style="soft"),
                Text(context.text.sentence()),
            )
        )


class CalloutGenerator:
    family = "callout"

    def __init__(self, paragraphs: ParagraphGenerator | None = None) -> None:
        self._paragraphs = paragraphs or ParagraphGenerator()

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, QuoteOptions(), QuoteOptions)
        kind = self._kind(context)
        title = ""
        if (
            context.supports("callout.title.custom")
            and context.rng.random() < options.title_ratio
        ):
            title = context.text.phrase(min_words=2, max_words=6, title_case=True)
        foldable = (
            context.supports("callout.foldable.expanded")
            or context.supports("callout.foldable.collapsed")
        ) and context.rng.random() < options.foldable_ratio
        collapsed = (
            foldable
            and context.supports("callout.foldable.collapsed")
            and context.rng.random() < 0.5
        )
        children: list[BlockNode] = [self._paragraphs.generate(context)]
        if (
            context.supports("callout.nested")
            and context.can_nest
            and context.rng.random() < options.nested_callout_ratio
        ):
            children.append(
                Callout(
                    kind=self._kind(context),
                    children=(self._paragraphs.generate(context.nested()),),
                )
            )
        return Callout(
            kind=kind,
            title=title,
            children=tuple(children),
            foldable=foldable,
            collapsed=collapsed,
        )

    def _kind(self, context: GenerationContext) -> str:
        candidates = [
            (feature, kind)
            for feature, kind in (
                *_GITHUB_CALLOUTS.items(),
                *_OBSIDIAN_CALLOUTS.items(),
            )
            if context.supports(feature)
        ]
        if not candidates:
            return "note"
        chosen = context.weighted_feature([feature for feature, _ in candidates])
        return next(kind for feature, kind in candidates if feature == chosen)


__all__ = ["CalloutGenerator", "QuoteGenerator", "QuoteOptions"]
