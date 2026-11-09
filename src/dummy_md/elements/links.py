"""Link generation across inline, reference, and autolink forms."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    Autolink,
    BlockNode,
    InlineNode,
    Link,
    LinkDefinition,
    Paragraph,
    Text,
)
from dummy_md.elements._util import resolve_options

_REFERENCE_FEATURES = (
    "link.reference.full",
    "link.reference.collapsed",
    "link.reference.shortcut",
    "link.definition",
)


@dataclass(frozen=True, slots=True)
class LinkOptions:
    min_links: int = 1
    max_links: int = 3
    title_ratio: float = 0.35
    reference_ratio: float = 0.4


class LinkGenerator:
    family = "link"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, LinkOptions(), LinkOptions)
        features = context.active_in_family("link")
        count = context.rng.randint(options.min_links, options.max_links)
        children: list[InlineNode] = []

        for index in range(count):
            if index:
                children.append(Text(" "))
            reference = self._reference_feature(features)
            if reference and context.rng.random() < options.reference_ratio:
                children.append(self._reference_link(context, features, reference))
                if (
                    context.supports("link.definition.shared")
                    and context.rng.random() < 0.4
                ):
                    children.append(Text(" "))
                    children.append(self._same_definition(context, children[-2]))
            else:
                children.append(self._plain_link(context, features, options))

        return Paragraph(children=tuple(children))

    # -- forms ------------------------------------------------------------
    def _plain_link(
        self,
        context: GenerationContext,
        features: tuple[str, ...],
        options: LinkOptions,
    ) -> InlineNode:
        autolink = self._autolink(context, features)
        if autolink is not None:
            return autolink

        if "link.inline" not in features and not any(
            feature.startswith("link.path.") for feature in features
        ):
            return Text(context.text.url())

        destination = self._destination(context, features)
        title = ""
        delimiter = '"'
        if (
            context.supports("link.title.double")
            and context.rng.random() < options.title_ratio
        ):
            title = context.text.phrase(min_words=2, max_words=5, title_case=True)
        elif (
            context.supports("link.title.paren")
            and context.rng.random() < options.title_ratio
        ):
            title = context.text.phrase(min_words=2, max_words=5, title_case=True)
            delimiter = "("
        return Link(
            children=(Text(context.text.label()),),
            destination=destination,
            title=title,
            title_delimiter=delimiter,  # type: ignore[arg-type]
        )

    def _reference_link(
        self,
        context: GenerationContext,
        features: tuple[str, ...],
        reference: str,
    ) -> InlineNode:
        label = context.refs.link_label()
        destination = context.text.url()
        title = ""
        if context.supports("link.title.double") and context.rng.random() < 0.3:
            title = context.text.phrase(min_words=2, max_words=4, title_case=True)
        context.refs.add_link(
            LinkDefinition(label=label, destination=destination, title=title)
        )
        kind = {
            "link.reference.full": "full",
            "link.reference.collapsed": "collapsed",
            "link.reference.shortcut": "shortcut",
        }.get(reference, "full")
        children: tuple[InlineNode, ...]
        if kind == "collapsed":
            children = (Text(label),)
        else:
            children = (Text(context.text.label()),)
        return Link(children=children, kind=kind, label=label)  # type: ignore[arg-type]

    def _same_definition(
        self, context: GenerationContext, previous: InlineNode | None
    ) -> InlineNode:
        label = previous.label if isinstance(previous, Link) else "ref-1"
        return Link(
            children=(Text(context.text.label()),),
            kind="full",
            label=label,
        )

    def _autolink(
        self, context: GenerationContext, features: tuple[str, ...]
    ) -> InlineNode | None:
        choices: list[str] = []
        for feature in (
            "link.autolink.uri",
            "link.autolink.email",
            "link.autolink.bare_url",
            "link.autolink.bare_www",
            "link.autolink.bare_email",
            "link.mailto",
        ):
            if feature in features:
                choices.append(feature)
        if not choices:
            return None
        feature = context.rng.choice(choices)
        if feature == "link.autolink.uri":
            return Autolink(target=context.text.url())
        if feature == "link.autolink.email":
            return Autolink(target=context.text.email(), is_email=True)
        if feature == "link.autolink.bare_url":
            return Autolink(target=context.text.url(), bracketed=False)
        if feature == "link.autolink.bare_www":
            return Autolink(
                target=f"www.{context.text.slug()}.example", bracketed=False
            )
        if feature == "link.autolink.bare_email":
            return Autolink(target=context.text.email(), is_email=True, bracketed=False)
        email = context.text.email()
        return Link(children=(Text(email),), destination=f"mailto:{email}")

    def _destination(
        self, context: GenerationContext, features: tuple[str, ...]
    ) -> str:
        choices = [
            feature
            for feature in (
                "link.path.relative",
                "link.path.root",
                "link.fragment",
                "link.destination.empty",
                "link.destination.angle",
                "link.to_document",
            )
            if feature in features
        ]
        if not choices:
            return context.text.url()
        feature = context.rng.choice(choices)
        if feature == "link.path.relative":
            return "docs/" + context.text.path()
        if feature == "link.path.root":
            return "/" + context.text.slug() + ".md"
        if feature == "link.fragment":
            return "#" + context.text.slug()
        if feature == "link.destination.empty":
            return ""
        if feature == "link.destination.angle":
            return f"docs/{context.text.slug()} {context.text.slug()}.md"
        return context.text.path(extension=".md")

    def _reference_feature(self, features: tuple[str, ...]) -> str | None:
        for feature in _REFERENCE_FEATURES:
            if feature in features:
                return feature
        return None
