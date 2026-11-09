"""Platform-specific Markdown: Obsidian, GitLab and documentation keys."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    BlockId,
    BlockNode,
    CodeBlock,
    CodeSpan,
    Embed,
    FrontMatter,
    InlineComment,
    ListBlock,
    ListItem,
    Paragraph,
    PlatformRef,
    PlatformRefKind,
    StyledSpan,
    Tag,
    Text,
    WikiLink,
)
from dummy_md.elements._util import resolve_options
from dummy_md.elements.paragraphs import ParagraphGenerator

_EMBEDS = {
    "platform.obsidian.transclusion": ("note", ""),
    "platform.obsidian.transclusion.heading": ("note", "heading"),
    "platform.obsidian.transclusion.block": ("note", "block"),
    "platform.obsidian.embed.pdf": ("manual.pdf", ""),
    "platform.obsidian.embed.audio": ("clip.mp3", ""),
    "platform.obsidian.embed.video": ("clip.mp4", ""),
    "platform.obsidian.embed.pdf_page": ("manual.pdf", "page"),
    "platform.obsidian.embed.width": ("diagram.png", ""),
    "platform.obsidian.embed.size": ("diagram.png", ""),
}

_PROPERTIES = {
    "platform.obsidian.property.text": ("status", "draft"),
    "platform.obsidian.property.list": ("tags", "[alpha, beta]"),
    "platform.obsidian.property.number": ("priority", "3"),
    "platform.obsidian.property.checkbox": ("published", "false"),
    "platform.obsidian.property.date": ("created", "2026-01-31"),
    "platform.obsidian.property.datetime": ("updated", "2026-01-31T12:00:00"),
    "platform.obsidian.property.tag": ("topic", "reference"),
}


_PLATFORM_FEATURES = frozenset(
    {
        "code.chunk.quarto",
        "code.chunk.quarto.inline",
        "code.highlight.docusaurus",
        "code.json_table.gitlab",
        "code.title.docusaurus",
        "list.task.inapplicable",
    }
    | {
        "platform.gitlab.color_chip",
        "platform.gitlab.commit_ref",
        "platform.gitlab.include",
        "platform.gitlab.issue_ref",
        "platform.gitlab.mention",
        "platform.gitlab.mr_ref",
        "platform.gitlab.placeholder",
        "platform.obsidian.block_id",
        "platform.obsidian.comment",
        "platform.obsidian.embed.audio",
        "platform.obsidian.embed.pdf",
        "platform.obsidian.embed.pdf_page",
        "platform.obsidian.embed.size",
        "platform.obsidian.embed.video",
        "platform.obsidian.embed.width",
        "platform.obsidian.highlight",
        "platform.obsidian.property.checkbox",
        "platform.obsidian.property.date",
        "platform.obsidian.property.datetime",
        "platform.obsidian.property.list",
        "platform.obsidian.property.number",
        "platform.obsidian.property.tag",
        "platform.obsidian.property.text",
        "platform.obsidian.tag",
        "platform.obsidian.tag.nested",
        "platform.obsidian.transclusion",
        "platform.obsidian.transclusion.block",
        "platform.obsidian.transclusion.heading",
        "platform.obsidian.wikilink.unresolved",
    }
)


@dataclass(frozen=True, slots=True)
class PlatformOptions:
    """Platform payloads are structural; no ratios are required yet."""


class PlatformGenerator:
    family = "platform"

    def __init__(self, paragraphs: ParagraphGenerator | None = None) -> None:
        self._paragraphs = paragraphs or ParagraphGenerator()

    def generate(self, context: GenerationContext) -> BlockNode:
        resolve_options(context, self.family, PlatformOptions(), PlatformOptions)
        feature = context.weighted_feature(
            [
                candidate
                for candidate in sorted(context.active_features)
                if candidate in _PLATFORM_FEATURES
            ]
        )
        if feature in _EMBEDS:
            return Paragraph(
                children=(Text("Embedded: "), self._embed(context, feature), Text("."))
            )
        if feature in _PROPERTIES:
            key, value = _PROPERTIES[feature]
            return FrontMatter(format="yaml", content=f"{key}: {value}")
        if feature == "list.task.inapplicable":
            return ListBlock(
                items=(
                    ListItem(
                        children=(self._paragraphs.generate(context),), marker="~"
                    ),
                    ListItem(children=(self._paragraphs.generate(context),)),
                )
            )
        if feature == "code.title.docusaurus":
            return CodeBlock(
                code="const answer = 42;",
                info="javascript",
                meta='title="example.js"',
                meta_feature=feature,
            )
        if feature == "code.highlight.docusaurus":
            return CodeBlock(
                code="const first = 1;\nconst second = 2;\nconst third = 3;",
                info="javascript",
                meta="{1,3}",
                meta_feature=feature,
            )
        if feature == "code.chunk.quarto":
            return CodeBlock(
                code="#| label: demo\n#| echo: false\nprint('chunk')",
                info="{python}",
                feature=feature,
            )
        if feature == "code.chunk.quarto.inline":
            return Paragraph(
                children=(
                    Text("Inline chunk: "),
                    CodeSpan(code="{python} 1 + 1", feature=feature),
                    Text("."),
                )
            )
        if feature == "code.json_table.gitlab":
            return CodeBlock(
                code='[{"name": "alpha", "value": 1}, {"name": "beta", "value": 2}]',
                info="json",
                feature=feature,
            )
        if feature == "platform.obsidian.tag":
            return Paragraph(children=(self._tag(context, "tag"),))
        if feature == "platform.obsidian.tag.nested":
            return Paragraph(children=(self._tag(context, "nested"),))
        if feature == "platform.obsidian.wikilink.unresolved":
            return Paragraph(
                children=(
                    WikiLink(
                        target=context.text.label(),
                        unresolved=True,
                    ),
                )
            )
        if feature == "platform.obsidian.block_id":
            return Paragraph(
                children=(
                    Text(context.text.sentence() + " "),
                    BlockId(feature=feature, name="block-" + context.text.slug()),
                )
            )
        if feature == "platform.obsidian.comment":
            return Paragraph(
                children=(
                    Text("Visible text "),
                    InlineComment(
                        feature=feature,
                        text=context.text.phrase(min_words=2, max_words=6),
                    ),
                    Text(" after comment."),
                )
            )
        if feature == "platform.obsidian.highlight":
            return Paragraph(
                children=(
                    StyledSpan(
                        children=(Text(context.text.phrase(min_words=2, max_words=4)),),
                        syntax="highlight",
                    ),
                )
            )
        if feature.startswith("platform.gitlab."):
            return Paragraph(children=(self._gitlab(context, feature),))
        return Paragraph(children=(Text(context.text.sentence()),))

    def _embed(self, context: GenerationContext, feature: str) -> Embed:
        target, fragment_kind = _EMBEDS[feature]
        fragment = ""
        width: int | None = None
        height: int | None = None
        if fragment_kind == "heading":
            fragment = context.text.heading_phrase(2)
        elif fragment_kind == "block":
            fragment = "^block-" + context.text.slug()
        elif fragment_kind == "page":
            fragment = f"page={context.text.number(1, 200)}"
        if feature == "platform.obsidian.embed.width":
            width = 320
        if feature == "platform.obsidian.embed.size":
            width, height = 320, 200
        return Embed(
            feature=feature,
            target=target,
            fragment=fragment,
            width=width,
            height=height,
        )

    def _tag(self, context: GenerationContext, kind: str) -> Tag:
        if kind == "nested":
            return Tag(
                feature="platform.obsidian.tag.nested",
                name=context.text.word() + "/" + context.text.word(),
            )
        return Tag(feature="platform.obsidian.tag", name=context.text.word())

    def _gitlab(self, context: GenerationContext, feature: str) -> PlatformRef:
        number = str(context.text.number(1, 900))
        mapping: dict[str, tuple[PlatformRefKind, str]] = {
            "platform.gitlab.issue_ref": ("issue", number),
            "platform.gitlab.mr_ref": ("merge_request", number),
            "platform.gitlab.mention": ("mention", context.text.word()),
            "platform.gitlab.commit_ref": ("commit", context.text.identifier()[:8]),
            "platform.gitlab.include": (
                "include",
                context.text.path(extension=".md"),
            ),
            "platform.gitlab.placeholder": ("placeholder", context.text.word()),
            "platform.gitlab.color_chip": (
                "color",
                context.text.choice(("1f75cb", "108548", "dd2b0e")),
            ),
        }
        kind, value = mapping[feature]
        return PlatformRef(
            feature=feature,
            kind=kind,
            value=value,
        )
