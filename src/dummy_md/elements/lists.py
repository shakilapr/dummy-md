"""List generation: nesting, tightness, task items, and mixed item content."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    BlockNode,
    Blockquote,
    CodeBlock,
    Heading,
    InlineNode,
    ListBlock,
    ListItem,
    Paragraph,
    Text,
)
from dummy_md.elements._util import resolve_options


@dataclass(frozen=True, slots=True)
class ListOptions:
    min_items: int = 2
    max_items: int = 6
    max_depth: int = 3
    nested_ratio: float = 0.45
    tight_ratio: float = 0.6
    task_ratio: float = 0.35
    ordered_ratio: float = 0.4
    multi_paragraph_ratio: float = 0.15
    extra_block_ratio: float = 0.18


class ListGenerator:
    family = "list"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, ListOptions(), ListOptions)
        return self._build(context, options, depth=0)

    def _item_paragraph(self, context: GenerationContext) -> Paragraph:
        sentences = context.rng.randint(1, 3)
        text = " ".join(
            context.text.sentence(min_words=4, max_words=10) for _ in range(sentences)
        )
        return Paragraph(children=(Text(text),))

    # -- construction -----------------------------------------------------
    def _build(
        self, context: GenerationContext, options: ListOptions, *, depth: int
    ) -> ListBlock:
        ordered = self._ordered(context, options)
        items: list[ListItem] = []
        ceiling = max(options.min_items, options.max_items - depth * 2)
        count = context.rng.randint(options.min_items, ceiling)
        for _ in range(count):
            items.append(self._item(context, options, depth=depth, ordered=ordered))
        tight = self._tight(context, options, items)
        return ListBlock(
            ordered=ordered,
            items=tuple(items),
            delimiter=self._delimiter(context, ordered),
            start=self._start(context),
            tight=tight,
        )

    def _item(
        self,
        context: GenerationContext,
        options: ListOptions,
        *,
        depth: int,
        ordered: bool,
    ) -> ListItem:
        children: list[BlockNode] = [self._item_paragraph(context)]

        if (
            context.supports("list.item.multiple_paragraphs")
            and context.rng.random() < options.multi_paragraph_ratio
        ):
            children.append(self._item_paragraph(context))

        if (
            context.supports("list.item.heading")
            and context.rng.random() < options.extra_block_ratio
        ):
            children.append(
                Heading(
                    level=context.rng.randint(2, 4),
                    children=(self._phrase(context),),
                )
            )

        if (
            context.supports("list.item.code_block")
            and context.rng.random() < options.extra_block_ratio
        ):
            children.append(
                CodeBlock(
                    code=context.text.sentence(min_words=2, max_words=6),
                    info="text",
                )
            )

        if (
            context.supports("list.item.blockquote")
            and context.rng.random() < options.extra_block_ratio
        ):
            children.append(Blockquote(children=(self._item_paragraph(context),)))

        if (
            depth + 1 < options.max_depth
            and context.depth + 1 < context.max_depth
            and context.can_nest
            and self._nested_available(context)
            and context.rng.random() < options.nested_ratio * (0.6**depth)
        ):
            children.append(self._nested(context, options, depth=depth + 1))

        checked = self._checked(context)
        return ListItem(children=tuple(children), checked=checked)

    def _nested(
        self, context: GenerationContext, options: ListOptions, *, depth: int
    ) -> ListBlock:
        child = context.nested()
        return self._build(child, options, depth=depth)

    def _nested_available(self, context: GenerationContext) -> bool:
        return any(
            context.supports(feature)
            for feature in (
                "list.nested.unordered",
                "list.nested.ordered",
                "list.nested.mixed",
                "list.task.nested",
            )
        )

    def _ordered(self, context: GenerationContext, options: ListOptions) -> bool:
        ordered_ok = context.supports_any(
            ("list.ordered.dot", "list.ordered.paren", "list.ordered.start")
        )
        unordered_ok = context.supports_any(
            ("list.unordered.hyphen", "list.unordered.asterisk", "list.unordered.plus")
        )
        if ordered_ok and unordered_ok:
            return context.rng.random() < options.ordered_ratio
        if ordered_ok:
            return True
        if unordered_ok:
            return False
        return False

    def _delimiter(self, context: GenerationContext, ordered: bool) -> str:
        if ordered:
            choices = [
                delimiter
                for feature, delimiter in (
                    ("list.ordered.dot", "."),
                    ("list.ordered.paren", ")"),
                )
                if context.supports(feature)
            ]
            return context.rng.choice(choices) if choices else "."
        choices = [
            marker
            for feature, marker in (
                ("list.unordered.hyphen", "-"),
                ("list.unordered.asterisk", "*"),
                ("list.unordered.plus", "+"),
            )
            if context.supports(feature)
        ]
        return context.rng.choice(choices) if choices else "-"

    def _start(self, context: GenerationContext) -> int:
        if context.supports("list.ordered.start") and context.rng.random() < 0.35:
            return context.rng.randint(2, 9)
        return 1

    def _tight(
        self, context: GenerationContext, options: ListOptions, items: list[ListItem]
    ) -> bool:
        tight_ok = context.supports("list.tight")
        loose_ok = context.supports("list.loose")
        dense = any(len(item.children) > 1 for item in items)
        if dense:
            return False
        if tight_ok and loose_ok:
            return context.rng.random() < options.tight_ratio
        if tight_ok:
            return True
        if loose_ok:
            return False
        return True

    def _checked(self, context: GenerationContext) -> bool | None:
        task_features = (
            "list.task.unchecked",
            "list.task.checked",
            "list.task.mixed",
            "list.task.nested",
        )
        if not context.supports_any(task_features):
            return None
        options = resolve_options(context, self.family, ListOptions(), ListOptions)
        if context.rng.random() >= options.task_ratio:
            return None
        if context.supports("list.task.mixed"):
            return context.rng.random() < 0.5
        if context.supports("list.task.checked") and context.supports(
            "list.task.unchecked"
        ):
            return context.rng.random() < 0.5
        if context.supports("list.task.checked"):
            return True
        return False

    @staticmethod
    def _phrase(context: GenerationContext) -> InlineNode:
        return Text(context.text.phrase(min_words=1, max_words=4, title_case=True))


__all__ = ["ListGenerator", "ListOptions"]
