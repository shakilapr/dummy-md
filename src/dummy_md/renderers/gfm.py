"""GitHub Flavored Markdown serialization."""

from __future__ import annotations

from dummy_md.core.nodes import Alignment, Table, TableCell
from dummy_md.exceptions import DialectError
from dummy_md.renderers.commonmark import CommonMarkRenderer


class GFMRenderer(CommonMarkRenderer):
    """CommonMark plus pipe tables (task lists and strikethrough are guarded)."""

    def _table(self, node: Table) -> str:
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
                for index, text in enumerate(padded)
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
        width = max(3, width)
        if alignment == "left":
            return ":" + "-" * (width - 1)
        if alignment == "right":
            return "-" * (width - 1) + ":"
        if alignment == "center":
            return ":" + "-" * max(1, width - 2) + ":"
        return "-" * width


__all__ = ["GFMRenderer"]
