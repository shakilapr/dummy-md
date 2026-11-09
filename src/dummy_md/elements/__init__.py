"""Element generators.

Generators build AST blocks; they never emit Markdown syntax.
"""

from dummy_md.core.registry import ElementGenerator, Registry
from dummy_md.elements.code import CodeBlockGenerator, CodeOptions
from dummy_md.elements.diagrams import DiagramGenerator
from dummy_md.elements.footnotes import FootnoteGenerator, FootnoteOptions
from dummy_md.elements.frontmatter import FrontMatterGenerator, FrontMatterOptions
from dummy_md.elements.headings import HeadingGenerator, HeadingOptions
from dummy_md.elements.html import HTMLGenerator
from dummy_md.elements.images import ImageGenerator, ImageOptions
from dummy_md.elements.links import LinkGenerator, LinkOptions
from dummy_md.elements.lists import ListGenerator, ListOptions
from dummy_md.elements.math import MathGenerator
from dummy_md.elements.paragraphs import ParagraphGenerator, ParagraphOptions
from dummy_md.elements.quotes import CalloutGenerator, QuoteGenerator, QuoteOptions
from dummy_md.elements.tables import TableGenerator, TableOptions
from dummy_md.elements.thematic import ThematicBreakGenerator


def build_generators() -> dict[str, ElementGenerator]:
    """Construct the default generator set, sharing stateless helpers."""
    paragraphs = ParagraphGenerator()
    tables = TableGenerator()
    generators: list[ElementGenerator] = [
        HeadingGenerator(),
        paragraphs,
        ThematicBreakGenerator(),
        ListGenerator(paragraphs),
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
    "CodeBlockGenerator",
    "CodeOptions",
    "DiagramGenerator",
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
    "ParagraphGenerator",
    "ParagraphOptions",
    "QuoteGenerator",
    "QuoteOptions",
    "TableGenerator",
    "TableOptions",
    "ThematicBreakGenerator",
    "build_generators",
    "register",
]
