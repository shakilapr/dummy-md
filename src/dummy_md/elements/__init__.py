"""Element generators.

Generators build AST blocks; they never emit Markdown syntax.
"""

from dummy_md.core.registry import ElementGenerator, Registry
from dummy_md.elements._util import build_options
from dummy_md.elements.code import CodeBlockGenerator, CodeOptions
from dummy_md.elements.diagrams import DiagramGenerator, DiagramOptions
from dummy_md.elements.footnotes import FootnoteGenerator, FootnoteOptions
from dummy_md.elements.frontmatter import FrontMatterGenerator, FrontMatterOptions
from dummy_md.elements.headings import HeadingGenerator, HeadingOptions
from dummy_md.elements.html import HTMLGenerator
from dummy_md.elements.images import ImageGenerator, ImageOptions
from dummy_md.elements.links import LinkGenerator, LinkOptions
from dummy_md.elements.lists import ListGenerator, ListOptions
from dummy_md.elements.math import MathGenerator, MathOptions
from dummy_md.elements.paragraphs import ParagraphGenerator, ParagraphOptions
from dummy_md.elements.quotes import CalloutGenerator, QuoteGenerator, QuoteOptions
from dummy_md.elements.tables import TableGenerator, TableOptions
from dummy_md.elements.thematic import ThematicBreakGenerator, ThematicBreakOptions

OPTION_TYPES: dict[str, type] = {
    "heading": HeadingOptions,
    "paragraph": ParagraphOptions,
    "thematic_break": ThematicBreakOptions,
    "list": ListOptions,
    "table": TableOptions,
    "code": CodeOptions,
    "link": LinkOptions,
    "image": ImageOptions,
    "blockquote": QuoteOptions,
    "callout": QuoteOptions,
    "footnote": FootnoteOptions,
    "math": MathOptions,
    "diagram": DiagramOptions,
    "frontmatter": FrontMatterOptions,
}


def build_generators() -> dict[str, ElementGenerator]:
    """Construct the default generator set, sharing stateless helpers."""
    paragraphs = ParagraphGenerator()
    tables = TableGenerator()
    generators: list[ElementGenerator] = [
        HeadingGenerator(),
        paragraphs,
        ThematicBreakGenerator(),
        ListGenerator(),
        tables,
        CodeBlockGenerator(),
        LinkGenerator(),
        ImageGenerator(),
        QuoteGenerator(paragraphs, tables),
        CalloutGenerator(paragraphs),
        HTMLGenerator(),
        FootnoteGenerator(),
        MathGenerator(),
        DiagramGenerator(),
        FrontMatterGenerator(),
    ]
    return {generator.family: generator for generator in generators}


def register(registry: Registry) -> None:
    for generator in build_generators().values():
        registry.register_generator(generator)


__all__ = [
    "OPTION_TYPES",
    "CalloutGenerator",
    "CodeBlockGenerator",
    "CodeOptions",
    "DiagramGenerator",
    "DiagramOptions",
    "FootnoteGenerator",
    "FootnoteOptions",
    "FrontMatterGenerator",
    "FrontMatterOptions",
    "HeadingGenerator",
    "HeadingOptions",
    "HTMLGenerator",
    "ImageGenerator",
    "ImageOptions",
    "LinkGenerator",
    "LinkOptions",
    "ListGenerator",
    "ListOptions",
    "MathGenerator",
    "MathOptions",
    "ParagraphGenerator",
    "ParagraphOptions",
    "QuoteGenerator",
    "QuoteOptions",
    "TableGenerator",
    "TableOptions",
    "ThematicBreakGenerator",
    "ThematicBreakOptions",
    "build_generators",
    "build_options",
    "register",
]
