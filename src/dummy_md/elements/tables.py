"""GFM pipe-table generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

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
    TableStyle,
    Text,
)
from dummy_md.elements._util import check_range, check_ratio, resolve_options

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
    many_ratio: float = 0.2
    style_ratio: float = 0.3
    min_cell_words: int = 1
    max_cell_words: int = 3

    def __post_init__(self) -> None:
        check_range(self.min_rows, self.max_rows, "table rows")
        check_range(self.min_columns, self.max_columns, "table columns")
        if self.min_columns < 1:
            raise ValueError("tables need at least one column")
        check_range(self.min_cell_words, self.max_cell_words, "cell words")
        if self.min_cell_words < 1:
            raise ValueError("cells need at least one word")
        for name in (
            "numeric_ratio",
            "empty_ratio",
            "inline_ratio",
            "header_only_ratio",
            "caption_ratio",
            "many_ratio",
            "style_ratio",
        ):
            check_ratio(getattr(self, name), name)


class TableGenerator:
    family = "table"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, TableOptions(), TableOptions)
        columns = self._column_count(context, options)
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
            style=self._style(context, options),
        )

    def _style(self, context: GenerationContext, options: TableOptions) -> TableStyle:
        candidates = [
            feature
            for feature in ("table.simple", "table.multiline")
            if context.supports(feature)
        ]
        if not candidates or context.rng.random() >= options.style_ratio:
            return "pipe"
        chosen = context.weighted_feature(candidates)
        return cast(TableStyle, chosen.split(".")[1])

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

    def _column_count(self, context: GenerationContext, options: TableOptions) -> int:
        if (
            context.supports("table.columns.many")
            and context.rng.random() < options.many_ratio
        ):
            return context.rng.randint(options.max_columns + 2, options.max_columns + 6)
        return context.rng.randint(options.min_columns, options.max_columns)

    def _cell_count(self, context: GenerationContext, columns: int) -> int:
        if context.supports("table.rows.missing_cells") and context.rng.random() < 0.15:
            return max(1, columns - 1)
        if context.supports("table.rows.extra_cells") and context.rng.random() < 0.15:
            return columns + 1
        return columns

    def _alignment(self, context: GenerationContext) -> Alignment:
        candidates = [
            (feature, alignment)
            for feature, alignment in _ALIGNMENTS
            if context.supports(feature)
        ]
        if not candidates:
            return "default"
        if context.supports("table.align.mixed"):
            chosen = context.weighted_feature([feature for feature, _ in candidates])
            return next(
                alignment for feature, alignment in candidates if feature == chosen
            )
        return candidates[0][1]

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
        numeric_ratio = (
            options.numeric_ratio if context.supports("table.payload.numeric") else 0.0
        )
        text = context.text.table_cell(numeric_ratio=numeric_ratio)
        if not text.replace(".", "").isdigit():
            count = context.rng.randint(options.min_cell_words, options.max_cell_words)
            text = " ".join(context.text.words(count))
            if (
                context.supports("table.cell.escaped_pipe")
                and context.rng.random() < options.inline_ratio
            ):
                words = text.split(" ")
                text = words[0] + " | " + " ".join(words[1:] or ["x"])
        styles = [feature for feature in _CELL_STYLES if context.supports(feature)]
        if not styles or context.rng.random() >= options.inline_ratio:
            return (Text(text),)
        return self._styled(context, context.weighted_feature(styles), text)

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
