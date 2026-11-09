"""MDX generation: ESM, expressions and JSX payloads."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, MdxBlock, MdxInline, Paragraph, Text
from dummy_md.elements._util import resolve_options

_INLINE_FEATURES = {
    "mdx.expression.inline",
    "mdx.jsx.self_closing",
    "mdx.jsx.inline",
    "mdx.expression.comment",
}


@dataclass(frozen=True, slots=True)
class MdxOptions:
    """MDX payloads are structural; no ratios are required yet."""


class MdxGenerator:
    family = "mdx"

    def generate(self, context: GenerationContext) -> BlockNode:
        resolve_options(context, self.family, MdxOptions(), MdxOptions)
        feature = context.weighted_feature(context.active_in_family("mdx"))
        if feature in _INLINE_FEATURES:
            return Paragraph(
                children=(
                    Text("Value: "),
                    MdxInline(feature=feature, code=self._inline_code(feature)),
                    Text("."),
                )
            )
        if feature == "mdx.markdown.interleaved":
            return Paragraph(
                children=(
                    Text("Interleaved "),
                    MdxInline(feature=feature, code="<Badge />"),
                    Text(" markdown content."),
                )
            )
        return MdxBlock(feature=feature, code=self._block_code(context, feature))

    def _inline_code(self, feature: str) -> str:
        mapping = {
            "mdx.expression.inline": "{1 + 1}",
            "mdx.jsx.self_closing": "<Badge />",
            "mdx.jsx.inline": "<strong>inline</strong>",
            "mdx.expression.comment": "{/* inline comment */}",
        }
        return mapping[feature]

    def _block_code(self, context: GenerationContext, feature: str) -> str:
        name = context.text.identifier(style="PascalCase")
        mapping = {
            "mdx.import.default": "import Component from './Component'",
            "mdx.import.named": "import { Widget } from './widget'",
            "mdx.export.const": "export const metadata = { title: 'Demo' }",
            "mdx.export.function": (
                "export function Demo() {\n  return <span>Demo</span>\n}"
            ),
            "mdx.expression.block": (
                "{items.map((item) => (\n  <li key={item.id}>{item.label}</li>\n))}"
            ),
            "mdx.jsx.paired": "<Callout>Content</Callout>",
            "mdx.jsx.nested": "<Outer>\n  <Inner />\n</Outer>",
            "mdx.jsx.fragment": "<>\n  <First />\n  <Second />\n</>",
            "mdx.jsx.prop.string": '<Button label="Save" />',
            "mdx.jsx.prop.expression": "<Button onClick={() => save()} />",
            "mdx.jsx.prop.object": (
                "<Chart options={{ type: 'bar', data: [1, 2] }} />"
            ),
            "mdx.jsx.prop.spread": "<Button {...props} />",
            "mdx.jsx.block": (
                '<Callout type="note">\n\nMarkdown **inside** JSX.\n\n</Callout>'
            ),
            "mdx.expression.comment": "{/* block comment */}",
            "mdx.docusaurus.tabs": (
                '<Tabs>\n  <TabItem value="one" label="One">First</TabItem>\n'
                '  <TabItem value="two" label="Two">Second</TabItem>\n</Tabs>'
            ),
            "mdx.docusaurus.tabitem": (
                '<TabItem value="one" label="One">Content</TabItem>'
            ),
        }
        return mapping.get(feature, f"<{name} />")
