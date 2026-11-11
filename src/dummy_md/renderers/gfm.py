"""GitHub Flavored Markdown serialization.

Pipe tables are GFM; ``simple`` and ``multiline`` tables are Pandoc table
syntax. Pandoc only recognises simple tables that have a non-empty body, so the
renderer falls back to a pipe table whenever the Pandoc form would be invalid.
"""

from __future__ import annotations

from dummy_md.core.nodes import Alignment, Table, TableCell, text_content
from dummy_md.exceptions import DialectError
from dummy_md.renderers.base import escape_text
from dummy_md.renderers.commonmark import CommonMarkRenderer


def _pad_grid(text: str, width: int, alignment: Alignment) -> str:
    padding = max(0, width - len(text))
    if alignment == "right":
        return " " * padding + text
    if alignment == "center":
        left = padding // 2
        return " " * left + text + " " * (padding - left)
    return text + " " * padding


class GFMRenderer(CommonMarkRenderer):
    """CommonMark plus pipe tables and Pandoc simple/multiline tables."""

    def _table(self, node: Table) -> str:
        if node.style == "grid":
            return self._grid_table(node)
        for cell in (*node.header, *(cell for row in node.rows for cell in row)):
            if cell.colspan != 1 or cell.rowspan != 1:
                raise DialectError(
                    "row and column spans require grid tables",
                    dialects=("extended", "stress"),
                )
        pandoc_ready = _pandoc_table_supported(node)
        if node.style == "simple" and pandoc_ready:
            return self._simple_table(node)
        if node.style == "multiline" and pandoc_ready:
            return self._multiline_table(node)
        return self._pipe_table(node)

    # -- grid tables -------------------------------------------------------
    def _grid_table(self, node: Table) -> str:
        """Render a Pandoc-style grid table, including row/column spans.

        Pandoc's reader does not preserve spans in grid tables, but the syntax
        is the canonical fixed-width form used by MultiMarkdown and Emacs table
        mode, and every cell's text survives the round trip.
        """
        self.require_any(
            ("table.grid", "table.grid.colspan", "table.grid.rowspan"),
            "grid tables",
        )
        rows = (node.header, *node.rows)
        if not rows:
            return ""
        columns = max(sum(cell.colspan for cell in row) for row in rows if row)
        if columns < 1:
            return ""
        cells = [[self._cell(cell) for cell in row] for row in rows]
        occupancy: list[list[tuple[int, int, TableCell] | None]] = [
            [None] * columns for _ in rows
        ]
        origins: list[list[tuple[int, int, TableCell, str]]] = [[] for _ in rows]
        for row_index, row in enumerate(rows):
            column = 0
            for cell, text in zip(row, cells[row_index], strict=True):
                while column < columns and occupancy[row_index][column] is not None:
                    column += 1
                if column >= columns:
                    break
                span = min(cell.colspan, columns - column)
                for offset in range(cell.rowspan):
                    target = row_index + offset
                    if target >= len(rows):
                        break
                    for sub in range(span):
                        occupancy[target][column + sub] = (row_index, column, cell)
                origins[row_index].append((column, span, cell, text))
                column += span

        widths = [3] * columns
        for _row_index, row_origins in enumerate(origins):
            for column, span, _cell, text in row_origins:
                if span == 1:
                    widths[column] = max(widths[column], len(text) + 2)
                else:
                    total = sum(widths[column : column + span]) + span - 1
                    need = len(text) + 2
                    if need > total:
                        widths[column + span - 1] += need - total

        def region_boundaries(row_index: int) -> set[int]:
            result = {0, columns}
            for column, span, _cell, _text in origins[row_index]:
                result.add(column)
                result.add(column + span)
            return result

        def rule(boundary: int, header: bool) -> str:
            above = occupancy[boundary - 1] if boundary else [None] * columns
            below = occupancy[boundary] if boundary < len(rows) else [None] * columns
            above_boundaries = (
                region_boundaries(boundary - 1) if boundary else {0, columns}
            )
            below_boundaries = (
                region_boundaries(boundary) if boundary < len(rows) else {0, columns}
            )
            dash = "=" if header else "-"
            parts: list[str] = []
            for column in range(columns + 1):
                if column in (0, columns):
                    edge = 0 if column == 0 else columns - 1
                    outer_above = above[edge]
                    outer_below = below[edge]
                    continues = (
                        outer_above is not None
                        and outer_below is not None
                        and outer_above[:2] == outer_below[:2]
                        and 0 < boundary < len(rows)
                    )
                    parts.append("|" if continues else "+")
                elif (column in above_boundaries or column in below_boundaries) and (
                    (
                        above[column - 1] is None
                        or above[column] is not above[column - 1]
                    )
                    or (
                        below[column - 1] is None
                        or below[column] is not below[column - 1]
                    )
                ):
                    parts.append("+")
                else:
                    parts.append(dash)
                if column < columns:
                    span_above = above[column]
                    span_below = below[column]
                    spanning = (
                        span_above is not None
                        and span_below is not None
                        and span_above[:2] == span_below[:2]
                        and 0 < boundary < len(rows)
                    )
                    parts.append((" " if spanning else dash) * widths[column])
            return "".join(parts)

        lines = [rule(0, False)]
        for row_index in range(len(rows)):
            regions: list[tuple[int, int, str]] = []
            column = 0
            while column < columns:
                owner = occupancy[row_index][column]
                if owner is None:
                    regions.append((column, 1, ""))
                    column += 1
                    continue
                origin_row, origin_column, cell = owner
                span = min(cell.colspan, columns - origin_column)
                text = (
                    self._cell(cell)
                    if origin_row == row_index and origin_column == column
                    else ""
                )
                regions.append((origin_column, span, text))
                column = origin_column + span
            segments: list[str] = []
            for start, span, text in regions:
                total = sum(widths[start : start + span]) + span - 1
                alignment = (
                    node.alignments[start]
                    if start < len(node.alignments)
                    else "default"
                )
                inner = max(1, total - 2)
                segments.append(" " + _pad_grid(text, inner, alignment) + " ")
            lines.append("|" + "|".join(segments) + "|")
            if row_index == 0 and len(rows) > 1:
                lines.append(rule(1, True))
            elif row_index < len(rows) - 1:
                lines.append(rule(row_index + 1, False))
        lines.append(rule(len(rows), False))
        # The header rule is emitted by the first iteration; remove duplicate
        # body rule immediately after it.
        deduped: list[str] = []
        for line in lines:
            if deduped and line == deduped[-1] and set(line) <= {"+", "="}:
                continue
            deduped.append(line)
        rendered = "\n".join(deduped)
        if node.caption:
            rendered += f"\n\n: {escape_text(node.caption)}"
        return rendered

    # -- pipe tables -------------------------------------------------------
    def _pipe_table(self, node: Table) -> str:
        for cell in (*node.header, *(cell for row in node.rows for cell in row)):
            if cell.colspan != 1 or cell.rowspan != 1:
                raise DialectError(
                    "pipe tables cannot express row or column spans",
                    dialects=("extended", "stress"),
                )

        header_texts = [self._cell(cell) for cell in node.header]
        rows_texts = [[self._cell(cell) for cell in row] for row in node.rows]

        widths = [max(3, len(text)) for text in header_texts]
        for row in rows_texts:
            for index, text in enumerate(row[: len(widths)]):
                widths[index] = max(widths[index], len(text))

        if node.outer_pipes:
            header = (
                "| "
                + " | ".join(
                    self._pad(i, text, widths, node.alignments)
                    for i, text in enumerate(header_texts)
                )
                + " |"
            )
        else:
            header = " | ".join(
                self._pad(i, text, widths, node.alignments)
                for i, text in enumerate(header_texts)
            )

        separators = [
            self._alignment_cell(alignment, width)
            for alignment, width in zip(node.alignments, widths, strict=False)
        ]
        if node.outer_pipes:
            divider = "| " + " | ".join(separators) + " |"
        else:
            divider = " | ".join(separators)

        lines = [header, divider]
        for row in rows_texts:
            padded = list(row)
            missing = len(header_texts) - len(padded)
            if missing > 0:
                padded.extend([""] * missing)
            cells = [
                self._pad(index, text, widths, node.alignments)
                for index, text in enumerate(padded[: len(widths)])
            ]
            if node.outer_pipes:
                lines.append("| " + " | ".join(cells) + " |")
            else:
                lines.append(" | ".join(cells))

        rendered = "\n".join(lines)
        if node.caption:
            self.require("table.caption", "table captions")
            return f"{rendered}\n\n: {node.caption}"
        return rendered

    # -- Pandoc table styles ----------------------------------------------
    def _simple_table(self, node: Table) -> str:
        self.require("table.simple", "simple tables")
        header, rows = self._grid(node)
        widths = _widths(header, rows)
        lines = [
            _row(header, widths),
            "  ".join("-" * width for width in widths),
        ]
        lines.extend(_row(row, widths) for row in rows)
        rendered = "\n".join(lines)
        if node.caption:
            self.require("table.caption", "table captions")
            return f"{rendered}\n\n: {node.caption}"
        return rendered

    def _multiline_table(self, node: Table) -> str:
        self.require("table.multiline", "multiline tables")
        header, rows = self._grid(node)
        widths = _widths(header, rows)
        border = "  ".join("-" * width for width in widths)
        lines = [border, _row(header, widths), border]
        lines.extend(_row(row, widths) for row in rows)
        lines.append(border)
        rendered = "\n".join(lines)
        if node.caption:
            self.require("table.caption", "table captions")
            return f"{rendered}\n\n: {node.caption}"
        return rendered

    def _grid(self, node: Table) -> tuple[list[str], list[list[str]]]:
        header = [self._cell(cell) for cell in node.header]
        rows = [[self._cell(cell) for cell in row] for row in node.rows]
        return header, rows

    def _cell(self, cell: TableCell) -> str:
        rendered = "".join(
            self.render_inline(child, "table_cell") for child in cell.children
        )
        return _escape_table_pipes(rendered)

    @staticmethod
    def _pad(
        index: int, text: str, widths: list[int], alignments: tuple[Alignment, ...]
    ) -> str:
        width = widths[index] if index < len(widths) else len(text)
        alignment: Alignment = (
            alignments[index] if index < len(alignments) else "default"
        )
        if alignment == "right":
            return text.rjust(width)
        if alignment == "center":
            return text.center(width)
        return text.ljust(width)

    @staticmethod
    def _alignment_cell(alignment: Alignment, width: int) -> str:
        if alignment == "left":
            return ":" + "-" * (width - 1)
        if alignment == "right":
            return "-" * (width - 1) + ":"
        if alignment == "center":
            return ":" + "-" * (width - 2) + ":"
        return "-" * width


def _escape_table_pipes(text: str) -> str:
    """Escape unescaped pipes that would otherwise split a table cell."""
    result: list[str] = []
    for index, character in enumerate(text):
        if character == "|":
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and text[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                result.append("\\|")
                continue
        result.append(character)
    return "".join(result)


def _pandoc_table_supported(node: Table) -> bool:
    """Pandoc simple tables need a body row with at least one non-empty cell."""
    if not node.rows:
        return False
    return any(text_content(cell.children).strip() for row in node.rows for cell in row)


def _widths(header: list[str], rows: list[list[str]]) -> list[int]:
    widths = [max(1, len(text)) for text in header] or [1]
    for row in rows:
        for index, text in enumerate(row[: len(widths)]):
            widths[index] = max(widths[index], len(text))
    return widths


def _row(cells: list[str], widths: list[int]) -> str:
    """Pad and truncate a row to the header's column count."""
    padded = [
        (cells[index] if index < len(cells) else "").ljust(width)
        for index, width in enumerate(widths)
    ]
    return "  ".join(padded).rstrip() or " " * sum(widths)
