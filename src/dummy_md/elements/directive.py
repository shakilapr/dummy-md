"""Documentation directives for MyST, MkDocs and Quarto."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    BlockNode,
    DirectiveBlock,
    DirectiveInline,
    DirectiveStyle,
    Paragraph,
    Text,
)
from dummy_md.elements._util import check_ratio, resolve_options
from dummy_md.elements.paragraphs import ParagraphGenerator

_INLINE_FEATURES = {
    "directive.myst.role",
    "directive.myst.ref",
    "directive.myst.numref",
    "directive.myst.doc_ref",
    "directive.mkdocs.keys",
    "directive.mkdocs.icons",
    "directive.mkdocs.tooltip",
    "directive.quarto.shortcode",
}


@dataclass(frozen=True, slots=True)
class DirectiveOptions:
    title_ratio: float = 0.5
    option_ratio: float = 0.3

    def __post_init__(self) -> None:
        for name in ("title_ratio", "option_ratio"):
            check_ratio(getattr(self, name), name)


class DirectiveGenerator:
    family = "directive"

    def __init__(self, paragraphs: ParagraphGenerator | None = None) -> None:
        self._paragraphs = paragraphs or ParagraphGenerator()

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, DirectiveOptions(), DirectiveOptions
        )
        feature = context.weighted_feature(context.active_in_family("directive"))
        if feature in _INLINE_FEATURES:
            return Paragraph(
                children=(
                    Text("See "),
                    self._inline(context, feature),
                    Text(" for details."),
                )
            )
        return DirectiveBlock(
            feature=feature,
            style=self._style(feature),
            name=self._name(feature),
            argument=self._argument(context, feature),
            title=(
                context.text.phrase(min_words=2, max_words=6, title_case=True)
                if context.rng.random() < options.title_ratio
                else ""
            ),
            options=self._options(context, feature, options),
            children=(
                ()
                if feature == "directive.myst.include"
                else (self._paragraphs.generate(context),)
            ),
        )

    # -- helpers ----------------------------------------------------------
    def _style(self, feature: str) -> DirectiveStyle:
        if feature.startswith("directive.myst."):
            return "myst"
        if feature.startswith("directive.mkdocs."):
            return "mkdocs"
        return "quarto"

    def _name(self, feature: str) -> str:
        mapping = {
            "directive.myst.fenced": "note",
            "directive.myst.target": "target",
            "directive.myst.figure": "figure",
            "directive.myst.table": "table",
            "directive.myst.admonition": "admonition",
            "directive.myst.theorem": "theorem",
            "directive.myst.proof": "proof",
            "directive.myst.dropdown": "dropdown",
            "directive.myst.tab_set": "tab-set",
            "directive.myst.tab_item": "tab-item",
            "directive.myst.include": "include",
            "directive.mkdocs.admonition": "note",
            "directive.mkdocs.details": "details",
            "directive.mkdocs.tabs": "tabs",
            "directive.mkdocs.annotations": "annotations",
            "directive.quarto.callout": "callout",
            "directive.quarto.tabset": "tabset",
        }
        return mapping.get(feature, "note")

    def _argument(self, context: GenerationContext, feature: str) -> str:
        if feature in {"directive.myst.target"}:
            return context.text.identifier(style="kebab-case")
        if feature == "directive.myst.figure":
            return context.text.path(extension=".png")
        if feature == "directive.myst.include":
            return context.text.path(extension=".md")
        if feature == "directive.mkdocs.annotations":
            return 'print("annotated")  # (1)'
        if feature == "directive.quarto.callout":
            return context.text.choice(("note", "tip", "warning", "caution"))
        return ""

    def _options(
        self,
        context: GenerationContext,
        feature: str,
        options: DirectiveOptions,
    ) -> tuple[tuple[str, str], ...]:
        if context.rng.random() >= options.option_ratio:
            return ()
        if feature == "directive.myst.figure":
            return (
                ("alt", context.text.phrase(min_words=2, max_words=5)),
                ("width", "320px"),
            )
        if feature == "directive.myst.table":
            return (("caption", context.text.phrase(min_words=2, max_words=5)),)
        if feature == "directive.myst.theorem":
            return (("label", "thm:" + context.text.slug()),)
        return ()

    def _inline(self, context: GenerationContext, feature: str) -> DirectiveInline:
        if feature.startswith("directive.myst."):
            name = {
                "directive.myst.role": "emphasis",
                "directive.myst.ref": "ref",
                "directive.myst.numref": "numref",
                "directive.myst.doc_ref": "doc",
            }[feature]
            return DirectiveInline(
                feature=feature,
                style="myst",
                name=name,
                argument=(
                    context.text.identifier(style="kebab-case")
                    if name in {"ref", "numref", "doc"}
                    else context.text.phrase(min_words=1, max_words=3)
                ),
            )
        if feature.startswith("directive.mkdocs."):
            name = feature.rsplit(".", 1)[-1]
            if name == "keys":
                argument = "ctrl+alt+del"
            elif name == "icons":
                argument = "material-account"
            else:
                argument = "tooltip text"
            return DirectiveInline(
                feature=feature, style="mkdocs", name=name, argument=argument
            )
        return DirectiveInline(
            feature=feature,
            style="quarto",
            name="var",
            argument=context.text.word(),
        )
