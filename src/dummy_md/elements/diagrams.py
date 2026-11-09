"""Mermaid diagram generation as fenced blocks."""

from __future__ import annotations

from collections.abc import Callable

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, CodeBlock


def _node(context: GenerationContext) -> str:
    return context.text.identifier(style="PascalCase", word_count=1)


def _phrase(context: GenerationContext, words: int = 3) -> str:
    return context.text.phrase(min_words=2, max_words=words, title_case=True)


def _flowchart(context: GenerationContext) -> str:
    first = _node(context)
    second = _node(context)
    third = _node(context)
    return "\n".join(
        [
            "flowchart TD",
            f"    {first} --> {second}",
            f"    {second} --> {third}",
            f"    {first} --> {third}",
        ]
    )


def _sequence(context: GenerationContext) -> str:
    first = _node(context)
    second = _node(context)
    return "\n".join(
        [
            "sequenceDiagram",
            f"    participant {first}",
            f"    participant {second}",
            f"    {first}->>{second}: {context.text.word()}",
            f"    {second}-->>{first}: {context.text.word()}",
        ]
    )


def _class_diagram(context: GenerationContext) -> str:
    first = _node(context)
    second = _node(context)
    return "\n".join(
        [
            "classDiagram",
            f"    class {first} {{",
            "        +int id",
            f"        +{context.text.word()}()",
            "    }",
            f"    {first} <|-- {second}",
        ]
    )


def _state(context: GenerationContext) -> str:
    first = _node(context)
    second = _node(context)
    return "\n".join(
        [
            "stateDiagram-v2",
            f"    [*] --> {first}",
            f"    {first} --> {second}",
            "    --> [*]",
        ]
    )


def _er(context: GenerationContext) -> str:
    first = _node(context).upper()
    second = _node(context).upper()
    return "\n".join(
        [
            "erDiagram",
            f"    {first} ||--o{{ {second} : {context.text.word()}",
        ]
    )


def _gantt(context: GenerationContext) -> str:
    first = _phrase(context)
    second = _phrase(context)
    day = context.text.number(1, 9)
    return "\n".join(
        [
            "gantt",
            "    title Release plan",
            "    dateFormat YYYY-MM-DD",
            "    section Work",
            f"    {first} :a1, 2024-01-0{day}, 5d",
            f"    {second} :after a1, 3d",
        ]
    )


def _pie(context: GenerationContext) -> str:
    title = _phrase(context, 4)
    values = [context.text.number(10, 60) for _ in range(3)]
    return "\n".join(
        [
            f"pie title {title}",
            f'    "{context.text.word()}" : {values[0]}',
            f'    "{context.text.word()}" : {values[1]}',
            f'    "{context.text.word()}" : {values[2]}',
        ]
    )


def _gitgraph(context: GenerationContext) -> str:
    return "\n".join(
        [
            "gitGraph",
            "    commit",
            '    branch "feature"',
            "    checkout feature",
            "    commit",
            "    checkout main",
            "    merge feature",
        ]
    )


def _journey(context: GenerationContext) -> str:
    return "\n".join(
        [
            "journey",
            f"    title {_phrase(context, 4)}",
            "    section Start",
            f"      {context.text.word()}: 5: user",
            "    section Finish",
            f"      {context.text.word()}: 3: user",
        ]
    )


MERMAID_BODIES: dict[str, Callable[[GenerationContext], str]] = {
    "diagram.mermaid.flowchart": _flowchart,
    "diagram.mermaid.sequence": _sequence,
    "diagram.mermaid.class": _class_diagram,
    "diagram.mermaid.state": _state,
    "diagram.mermaid.er": _er,
    "diagram.mermaid.gantt": _gantt,
    "diagram.mermaid.pie": _pie,
    "diagram.mermaid.gitgraph": _gitgraph,
    "diagram.mermaid.journey": _journey,
}


class DiagramGenerator:
    family = "diagram"

    def generate(self, context: GenerationContext) -> BlockNode:
        features = [
            feature
            for feature in context.active_in_family("diagram")
            if feature in MERMAID_BODIES
        ]
        if features:
            body = MERMAID_BODIES[context.rng.choice(features)](context)
        else:
            body = _flowchart(context)
        return CodeBlock(code=body, info="mermaid")
