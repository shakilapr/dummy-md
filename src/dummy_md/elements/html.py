"""Raw HTML generation for the HTML feature family."""

from __future__ import annotations

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, HTMLBlock, Paragraph, RawHTML, Text


class HTMLGenerator:
    family = "html"

    def generate(self, context: GenerationContext) -> BlockNode:
        features = context.active_in_family("html")
        feature = context.weighted_feature(features) if features else "html.block"
        return self._build(context, feature)

    # -- dispatch ---------------------------------------------------------
    def _build(self, context: GenerationContext, feature: str) -> BlockNode:
        text = context.text.sentence(min_words=4, max_words=10)
        phrase = context.text.phrase(min_words=2, max_words=4, title_case=True)
        if feature == "html.inline" or feature == "html.span":
            return self._paragraph(
                context,
                RawHTML(content=f'<span class="{context.text.word()}">{text}</span>'),
            )
        if feature in {"html.kbd", "html.sup", "html.sub", "html.ruby"}:
            return self._inline_tag(context, feature)
        if feature == "html.comment":
            return HTMLBlock(block_type=2, content=f"<!-- {text} -->")
        if feature == "html.br":
            return self._paragraph(context, RawHTML(content="<br>"), suffix=" " + text)
        if feature == "html.hr":
            return HTMLBlock(block_type=6, content="<hr>")
        if feature == "html.details":
            return HTMLBlock(
                block_type=6,
                content=(
                    f"<details>\n<summary>{phrase}</summary>\n\n{text}\n\n</details>"
                ),
            )
        if feature == "html.summary":
            return HTMLBlock(
                block_type=6,
                content=f"<summary>{phrase}</summary>",
            )
        if feature == "html.details.nested":
            inner_summary = context.text.phrase(
                min_words=2, max_words=3, title_case=True
            )
            return HTMLBlock(
                block_type=6,
                content=(
                    "<details>\n"
                    f"<summary>{phrase}</summary>\n\n"
                    "<details>\n"
                    f"<summary>{inner_summary}</summary>\n\n"
                    f"{text}\n\n"
                    "</details>\n\n"
                    "</details>"
                ),
            )
        if feature in {"html.table", "html.thead", "html.tbody", "html.tfoot"}:
            return HTMLBlock(block_type=6, content=self._table(context, feature))
        if feature in {"html.table.rowspan", "html.table.colspan"}:
            span = "rowspan" if feature.endswith("rowspan") else "colspan"
            return HTMLBlock(
                block_type=6,
                content=(
                    "<table>\n"
                    f'  <tr><td {span}="2">{phrase}</td><td>{text}</td></tr>\n'
                    "  <tr><td>cell</td></tr>\n"
                    "</table>"
                ),
            )
        if feature == "html.colgroup":
            return HTMLBlock(
                block_type=6,
                content=(
                    '<table>\n  <colgroup><col span="2"></colgroup>\n'
                    f"  <tr><td>{phrase}</td><td>{text}</td></tr>\n</table>"
                ),
            )
        if feature == "html.img":
            return HTMLBlock(
                block_type=6,
                content=(
                    f'<img src="https://example.com/{context.text.slug()}.png" '
                    f'alt="{phrase}" width="320">'
                ),
            )
        if feature == "html.picture":
            return HTMLBlock(
                block_type=6,
                content=(
                    "<picture>\n"
                    f'  <source srcset="https://example.com/'
                    f'{context.text.slug()}.webp" '
                    'type="image/webp">\n'
                    f'  <img src="https://example.com/{context.text.slug()}.png" '
                    f'alt="{phrase}">\n'
                    "</picture>"
                ),
            )
        if feature in {"html.audio", "html.video"}:
            tag = feature.split(".")[1]
            source = context.text.slug()
            return HTMLBlock(
                block_type=6,
                content=(
                    f"<{tag} controls>\n"
                    f'  <source src="https://example.com/{source}.'
                    f'{"mp3" if tag == "audio" else "mp4"}" '
                    f'type="{"audio/mpeg" if tag == "audio" else "video/mp4"}">\n'
                    f"</{tag}>"
                ),
            )
        if feature == "html.iframe":
            return HTMLBlock(
                block_type=6,
                content=(
                    f'<iframe src="https://example.com/{context.text.slug()}" '
                    f'title="{phrase}" width="560" height="315"></iframe>'
                ),
            )
        if feature == "html.svg.inline":
            return self._paragraph(
                context,
                Text(" "),
                RawHTML(
                    content=(
                        '<svg width="120" height="40" '
                        'xmlns="http://www.w3.org/2000/svg">'
                        '<rect width="120" height="40" fill="none" '
                        'stroke="currentColor"/>'
                        f'<text x="8" y="24">{phrase}</text></svg>'
                    )
                ),
            )
        if feature == "html.parsed_markdown":
            return HTMLBlock(
                block_type=6,
                content=(
                    '<div markdown="1">\n\n'
                    f"**{phrase}** and _emphasis_ inside HTML.\n\n"
                    "</div>"
                ),
            )
        tags = {
            "html.div": "div",
            "html.section": "section",
            "html.article": "article",
            "html.aside": "aside",
        }
        if feature in tags:
            tag = tags[feature]
            return HTMLBlock(block_type=6, content=f"<{tag}>\n{text}\n</{tag}>")
        return HTMLBlock(block_type=6, content=f"<div>\n{text}\n</div>")

    def _paragraph(
        self, context: GenerationContext, *nodes: object, suffix: str = ""
    ) -> Paragraph:
        children: list[object] = [Text(context.text.sentence(min_words=3, max_words=6))]
        children.extend(nodes)
        if suffix:
            children.append(Text(suffix))
        return Paragraph(children=tuple(children))  # type: ignore[arg-type]

    def _inline_tag(self, context: GenerationContext, feature: str) -> BlockNode:
        text = context.text.phrase(min_words=1, max_words=3)
        if feature == "html.kbd":
            markup = f"<kbd>Ctrl</kbd>+<kbd>{text[:1].upper()}</kbd>"
        elif feature == "html.sup":
            markup = f"x<sup>2</sup> = {context.text.number(1, 99)}"
        elif feature == "html.sub":
            markup = f"H<sub>2</sub>O ({context.text.word()})"
        else:
            markup = f"<ruby>{text}<rp>(</rp><rt>{text[:4]}</rt><rp>)</rp></ruby>"
        return self._paragraph(
            context, RawHTML(content=markup), suffix=" " + context.text.word()
        )

    def _table(self, context: GenerationContext, feature: str) -> str:
        rows = "\n".join(
            f"    <tr><td>{context.text.word()}</td>"
            f"<td>{context.text.number(0, 99)}</td></tr>"
            for _ in range(context.text.number(1, 3))
        )
        head = "<thead>\n    <tr><th>Name</th><th>Value</th></tr>\n  </thead>"
        body = f"<tbody>\n{rows}\n  </tbody>"
        foot = ""
        if feature == "html.tfoot":
            foot = "\n  <tfoot>\n    <tr><td>total</td><td>0</td></tr>\n  </tfoot>"
        return f"<table>\n  {head}\n  {body}{foot}\n</table>"
