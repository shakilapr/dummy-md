"""Fenced and indented code block generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import Attributes, BlockNode, CodeBlock
from dummy_md.elements._util import check_ratio, resolve_options
from dummy_md.elements.payloads import CODE_PAYLOADS, Payload


@dataclass(frozen=True, slots=True)
class CodeOptions:
    indented_ratio: float = 0.2
    long_fence_ratio: float = 0.2
    info_ratio: float = 0.85
    attribute_ratio: float = 0.2
    caption_ratio: float = 0.15

    def __post_init__(self) -> None:
        for name in (
            "indented_ratio",
            "long_fence_ratio",
            "info_ratio",
            "attribute_ratio",
            "caption_ratio",
        ):
            check_ratio(getattr(self, name), name)


class CodeBlockGenerator:
    family = "code"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, CodeOptions(), CodeOptions)
        active = context.active_in_family("code")
        if context.supports("stress.whitespace.tabs"):
            return CodeBlock(
                code="\talpha\tbeta\n\tgamma\tdelta",
                info="text",
                feature="stress.whitespace.tabs",
            )
        payload = self._payload(context, active)
        code = payload.build(context) if payload else context.text.sentence()

        if context.supports("code.indented") and (
            not context.supports("code.fenced.backtick")
            or context.rng.random() < options.indented_ratio
        ):
            return CodeBlock(code=code, indented=True)

        fence_char = self._fence_character(context)
        fence_length = 3
        if (
            context.supports("code.fence.long")
            and context.rng.random() < options.long_fence_ratio
        ):
            fence_length = context.rng.randint(4, 6)

        info = ""
        if payload is not None and context.supports("code.info"):
            info = payload.language
        if not info and context.supports("code.no_info"):
            info = ""
        if info and context.rng.random() > options.info_ratio:
            info = ""

        attributes = self._attributes(context, options)
        feature = ""
        if context.supports("code.line_numbers"):
            pairs: tuple[tuple[str, str], ...] = attributes.pairs if attributes else ()
            pairs = (*pairs, ("numberLines", ""))
            attributes = Attributes(
                identifier=attributes.identifier if attributes else None,
                classes=attributes.classes if attributes else (),
                pairs=pairs,
            )
            feature = "code.line_numbers"
        annotations: tuple[str, ...] = ()
        if context.supports_any(("code.annotations", "code.annotations.inline")):
            annotations = tuple(
                context.text.phrase(min_words=2, max_words=5)
                for _ in range(context.rng.randint(1, 3))
            )
            if context.supports("code.annotations.inline"):
                code = code + "  # (1)"
        caption = ""
        if (
            context.supports("code.caption")
            and context.rng.random() < options.caption_ratio
        ):
            caption = context.text.phrase(min_words=3, max_words=7, title_case=True)

        return CodeBlock(
            code=code,
            info=info,
            fence_char=fence_char,
            fence_length=fence_length,
            attributes=attributes,
            caption=caption,
            annotations=annotations,
            feature=feature,
        )

    # -- helpers ----------------------------------------------------------
    def _payload(
        self, context: GenerationContext, active: tuple[str, ...]
    ) -> Payload | None:
        candidates = [
            payload for payload in CODE_PAYLOADS if payload.feature_id in active
        ]
        if not candidates:
            return None
        chosen = context.weighted_feature(
            [payload.feature_id for payload in candidates]
        )
        return next(payload for payload in candidates if payload.feature_id == chosen)

    def _fence_character(self, context: GenerationContext) -> Literal["`", "~"]:
        backtick = context.supports("code.fenced.backtick")
        tilde = context.supports("code.fenced.tilde")
        if backtick and tilde:
            return "`" if context.rng.random() < 0.65 else "~"
        if tilde and not backtick:
            return "~"
        return "`"

    def _attributes(
        self, context: GenerationContext, options: CodeOptions
    ) -> Attributes | None:
        if context.rng.random() >= options.attribute_ratio:
            return None
        identifier = None
        classes: tuple[str, ...] = ()
        if context.supports("code.attributes.identifier"):
            identifier = context.text.identifier(style="kebab-case")
        if context.supports("code.attributes.classes"):
            classes = (context.text.word(min_length=3, max_length=8),)
        if identifier is None and not classes:
            return None
        return Attributes(identifier=identifier, classes=classes)
