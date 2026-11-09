"""Image generation: inline, reference, figures, and embedded lists/tables."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import (
    Alignment,
    BlockNode,
    Figure,
    Image,
    Link,
    LinkDefinition,
    ListBlock,
    ListItem,
    Paragraph,
    Table,
    TableCell,
    Text,
)
from dummy_md.elements._util import check_ratio, resolve_options


@dataclass(frozen=True, slots=True)
class ImageOptions:
    title_ratio: float = 0.4
    remote_ratio: float = 0.5
    reference_ratio: float = 0.25
    size_ratio: float = 0.3
    in_table_ratio: float = 0.3
    in_list_ratio: float = 0.2
    in_link_ratio: float = 0.2
    figure_ratio: float = 0.3

    def __post_init__(self) -> None:
        for name in (
            "title_ratio",
            "remote_ratio",
            "reference_ratio",
            "size_ratio",
            "in_table_ratio",
            "in_list_ratio",
            "in_link_ratio",
            "figure_ratio",
        ):
            check_ratio(getattr(self, name), name)


class ImageGenerator:
    family = "image"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, ImageOptions(), ImageOptions)
        features = context.active_in_family("image")

        if (
            "image.in_table" in features
            and context.rng.random() < options.in_table_ratio
        ):
            return self._in_table(context)
        if "image.in_list" in features and context.rng.random() < options.in_list_ratio:
            return self._in_list(context)

        image = self._image(context, features, options)
        if (
            "image.figure.implicit" in features
            and context.rng.random() < options.figure_ratio
        ):
            return Figure(
                image=image,
                caption=context.text.phrase(min_words=4, max_words=9, title_case=True),
                implicit=True,
            )
        if (
            "image.figure.caption" in features or "image.figure.label" in features
        ) and context.rng.random() < options.figure_ratio:
            return Figure(
                image=image,
                caption=(
                    context.text.phrase(min_words=4, max_words=9, title_case=True)
                    if "image.figure.caption" in features
                    else ""
                ),
                label=(
                    "fig:" + context.text.slug()
                    if "image.figure.label" in features
                    else ""
                ),
            )
        if "image.in_link" in features and context.rng.random() < options.in_link_ratio:
            return Paragraph(
                children=(
                    Link(
                        children=(image,),
                        destination=context.text.url(),
                    ),
                )
            )
        return Paragraph(children=(image,))

    # -- helpers ----------------------------------------------------------
    def _image(
        self,
        context: GenerationContext,
        features: tuple[str, ...],
        options: ImageOptions,
    ) -> Image:
        alt_text = context.text.label()
        if "image.alt.escaped" in features and context.rng.random() < 0.3:
            alt_text = f"{alt_text} [sic] *draft*"

        if (
            "image.url.remote" in features
            and context.rng.random() < options.remote_ratio
        ):
            destination = context.text.url()
        elif "image.path.relative" in features:
            destination = context.text.path(extension=".png")
        else:
            destination = context.text.url()

        title = ""
        if "image.title" in features and context.rng.random() < options.title_ratio:
            title = context.text.phrase(min_words=2, max_words=5, title_case=True)

        kind = "inline"
        label = ""
        if (
            "image.reference" in features
            and context.block_hint >= 400
            and context.rng.random() < options.reference_ratio
        ):
            label = context.refs.link_label("img")
            context.refs.add_link(
                LinkDefinition(label=label, destination=destination, title=title)
            )
            kind = "full"

        width: int | None = None
        height: int | None = None
        if "image.width" in features and context.rng.random() < options.size_ratio:
            width = context.rng.choice((160, 240, 320, 480))
        if "image.height" in features and context.rng.random() < options.size_ratio / 2:
            height = context.rng.choice((120, 180, 240))

        return Image(
            alt=(Text(alt_text),),
            destination=destination,
            title=title,
            kind=kind,  # type: ignore[arg-type]
            label=label,
            width=width,
            height=height,
        )

    def _in_list(self, context: GenerationContext) -> BlockNode:
        features = context.active_in_family("image")
        image = self._image(context, features, ImageOptions())
        return ListBlock(
            items=(ListItem(children=(Paragraph(children=(Text("see "), image)),)),)
        )

    def _in_table(self, context: GenerationContext) -> BlockNode:
        features = context.active_in_family("image")
        image = self._image(context, features, ImageOptions())
        cell = TableCell(children=(image,))
        alignments: tuple[Alignment, ...] = ("center",)
        return Table(
            header=(TableCell(children=(Text("Preview"),)),),
            rows=((cell,),),
            alignments=alignments,
        )
