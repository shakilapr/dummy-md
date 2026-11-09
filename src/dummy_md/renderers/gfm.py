"""GitHub Flavored Markdown serialization.

Pipe tables are GFM; ``simple`` and ``multiline`` tables are Pandoc table
syntax. Pandoc only recognises simple tables that have a non-empty body, so the
renderer falls back to a pipe table whenever the Pandoc form would be invalid.
"""

from __future__ import annotations

from dummy_md.core.nodes import Alignment, Table, TableCell, text_content
from dummy_md.exceptions import DialectError
from dummy_md.renderers.commonmark import CommonMarkRenderer


class GFMRenderer(CommonMarkRenderer):
    """CommonMark plus pipe tables and Pandoc simple/multiline tables."""

    def _table(self, node: Table) -> str:
        pandoc_ready = _pandoc_table_supported(node)
        if node.style == "simple" and pandoc_ready:
            return self._simple_table(node)
        if node.style == "multiline" and pandoc_ready:
            return self._multiline_table(node)
        return self._pipe_table(node)

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
        return "".join(
            self.render_inline(child, "table_cell") for child in cell.children
        )

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
