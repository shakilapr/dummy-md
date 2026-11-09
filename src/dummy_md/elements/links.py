"""Link generation across inline, reference, and autolink forms."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    Attributes,
    Autolink,
    BlockNode,
    InlineNode,
    Link,
    LinkDefinition,
    Paragraph,
    Text,
    WikiLink,
)
from dummy_md.elements._util import check_ratio, resolve_options

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
    wiki_ratio: float = 0.4

    def __post_init__(self) -> None:
        if self.min_links < 1:
            raise ValueError("min_links must be at least 1")
        if self.max_links < self.min_links:
            raise ValueError("max_links must be >= min_links")
        for name in ("title_ratio", "reference_ratio", "wiki_ratio"):
            check_ratio(getattr(self, name), name)


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
            wiki = self._wiki(context, options)
            if wiki is not None:
                children.append(wiki)
                continue
            reference = (
                self._reference_feature(features) if context.block_hint >= 400 else None
            )
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
    def _wiki(
        self, context: GenerationContext, options: LinkOptions
    ) -> InlineNode | None:
        if not context.supports("link.wiki.basic"):
            return None
        if context.rng.random() >= options.wiki_ratio:
            return None
        return self._wiki_node(context)

    def _wiki_node(self, context: GenerationContext) -> WikiLink:
        target = context.text.label()
        return WikiLink(
            target=target,
            alias=(
                context.text.label()
                if context.supports("link.wiki.alias") and context.rng.random() < 0.5
                else ""
            ),
            heading=(
                context.text.heading_phrase(2)
                if context.supports("link.wiki.heading") and context.rng.random() < 0.4
                else ""
            ),
            block=(
                "block-" + context.text.slug()
                if context.supports("link.wiki.block") and context.rng.random() < 0.3
                else ""
            ),
        )

    def _plain_link(
        self,
        context: GenerationContext,
        features: tuple[str, ...],
        options: LinkOptions,
    ) -> InlineNode:
        if context.supports("stress.url.percent_encoded"):
            return Link(
                children=(Text(context.text.label()),),
                destination="https://example.com/%E2%9C%93/path%20with%20spaces",
            )
        autolink = self._autolink(context, features)
        if autolink is not None:
            return autolink

        if "link.inline" not in features and not any(
            feature.startswith("link.path.") for feature in features
        ):
            if context.supports("link.wiki.basic"):
                return self._wiki_node(context)
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
            attributes=(
                Attributes(classes=(context.text.word(),))
                if context.supports("link.attributes") and context.rng.random() < 0.3
                else None
            ),
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
        feature = context.weighted_feature(choices)
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
        feature = context.weighted_feature(choices)
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
