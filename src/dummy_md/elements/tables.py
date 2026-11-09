"""GFM pipe-table generation."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    Alignment,
    BlockNode,
    CodeSpan,
    Emphasis,
    Image,
    InlineNode,
    Link,
    RawHTML,
    Strikethrough,
    Table,
    TableCell,
    Text,
)
from dummy_md.elements._util import resolve_options

_CELL_STYLES = (
    "table.cell.bold",
    "table.cell.italic",
    "table.cell.strikethrough",
    "table.cell.code",
    "table.cell.link",
    "table.cell.image",
    "table.cell.html_break",
)

_ALIGNMENTS: tuple[tuple[str, Alignment], ...] = (
    ("table.align.left", "left"),
    ("table.align.right", "right"),
    ("table.align.center", "center"),
    ("table.align.default", "default"),
)


@dataclass(frozen=True, slots=True)
class TableOptions:
    min_rows: int = 2
    max_rows: int = 6
    min_columns: int = 2
    max_columns: int = 4
    numeric_ratio: float = 0.3
    empty_ratio: float = 0.08
    inline_ratio: float = 0.3
    header_only_ratio: float = 0.1
    caption_ratio: float = 0.25


class TableGenerator:
    family = "table"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, TableOptions(), TableOptions)
        columns = context.rng.randint(options.min_columns, options.max_columns)
        rows = self._row_count(context, options)
        alignments = tuple(self._alignment(context) for _ in range(columns))

        header = tuple(
            TableCell(
                children=(
                    Text(
                        context.text.phrase(min_words=1, max_words=3, title_case=True)
                    ),
                )
            )
            for _ in range(columns)
        )
        body = tuple(
            tuple(
                self._cell(context, options)
                for _ in range(self._cell_count(context, columns))
            )
            for _ in range(rows)
        )

        outer_pipes = True
        if context.supports("table.pipe.no_outer") and context.rng.random() < 0.3:
            outer_pipes = False

        caption = ""
        if (
            context.supports("table.caption")
            and context.rng.random() < options.caption_ratio
        ):
            caption = context.text.phrase(min_words=3, max_words=7, title_case=True)

        return Table(
            header=header,
            rows=body,
            alignments=alignments,
            outer_pipes=outer_pipes,
            caption=caption,
        )

    # -- helpers ----------------------------------------------------------
    def _row_count(self, context: GenerationContext, options: TableOptions) -> int:
        if context.supports("table.rows.many"):
            return context.rng.randint(options.max_rows, options.max_rows * 2)
        if (
            context.supports("table.header_only")
            and context.rng.random() < options.header_only_ratio
        ):
            return 0
        return context.rng.randint(options.min_rows, options.max_rows)

    def _cell_count(self, context: GenerationContext, columns: int) -> int:
        if context.supports("table.rows.missing_cells") and context.rng.random() < 0.15:
            return max(1, columns - 1)
        if context.supports("table.rows.extra_cells") and context.rng.random() < 0.15:
            return columns + 1
        return columns

    def _alignment(self, context: GenerationContext) -> Alignment:
        choices: list[Alignment] = [
            alignment for feature, alignment in _ALIGNMENTS if context.supports(feature)
        ]
        if not choices:
            return "default"
        if context.supports("table.align.mixed"):
            return context.rng.choice(choices)
        return choices[0]

    def _cell(self, context: GenerationContext, options: TableOptions) -> TableCell:
        children = self._cell_children(context, options)
        return TableCell(children=children)

    def _cell_children(
        self, context: GenerationContext, options: TableOptions
    ) -> tuple[InlineNode, ...]:
        if (
            context.supports("table.cell.empty")
            and context.rng.random() < options.empty_ratio
        ):
            return ()
        text = context.text.table_cell(numeric_ratio=options.numeric_ratio)
        styles = [feature for feature in _CELL_STYLES if context.supports(feature)]
        if not styles or context.rng.random() >= options.inline_ratio:
            return (Text(text),)
        return self._styled(context, context.rng.choice(styles), text)

    def _styled(
        self, context: GenerationContext, feature: str, text: str
    ) -> tuple[InlineNode, ...]:
        if feature == "table.cell.bold":
            return (Emphasis(children=(Text(text),), level=2),)
        if feature == "table.cell.italic":
            return (Emphasis(children=(Text(text),), level=1),)
        if feature == "table.cell.strikethrough":
            return (Strikethrough(children=(Text(text),)),)
        if feature == "table.cell.code":
            return (CodeSpan(code=text),)
        if feature == "table.cell.link":
            return (
                Link(
                    children=(Text(text),),
                    destination=context.text.url(),
                ),
            )
        if feature == "table.cell.image":
            return (
                Image(
                    alt=(Text(text),),
                    destination=context.text.path(extension=".png"),
                ),
            )
        return (RawHTML(content="<br>"), Text(" " + text))
