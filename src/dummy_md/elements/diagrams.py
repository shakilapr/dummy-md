"""Mermaid diagram generation as fenced blocks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, CodeBlock
from dummy_md.elements._util import resolve_options


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


def _swimlane(context: GenerationContext) -> str:
    return "\n".join(
        [
            "flowchart LR",
            "    subgraph Requests",
            f"        {_node(context)} --> {_node(context)}",
            "    end",
            "    subgraph Storage",
            f"        {_node(context)}",
            "    end",
        ]
    )


def _quadrant(context: GenerationContext) -> str:
    return "\n".join(
        [
            "quadrantChart",
            f"    title {_phrase(context, 4)}",
            "    x-axis Low --> High",
            "    y-axis Low --> High",
            "    quadrant-1 Expand",
            "    quadrant-2 Maintain",
            "    quadrant-3 Review",
            "    quadrant-4 Retire",
            f"    {_node(context)}: [0.3, 0.7]",
            f"    {_node(context)}: [0.7, 0.4]",
        ]
    )


def _requirement(context: GenerationContext) -> str:
    return "\n".join(
        [
            "requirementDiagram",
            "    requirement req1 {",
            "        id: 1",
            f"        text: {_phrase(context, 4)}",
            "        risk: medium",
            "        verifymethod: test",
            "    }",
        ]
    )


def _c4(context: GenerationContext) -> str:
    first = _node(context)
    second = _node(context)
    return "\n".join(
        [
            "C4Context",
            f"    title {_phrase(context, 4)}",
            f'    Person({first}, "{_phrase(context, 2)}")',
            f'    System({second}, "{_phrase(context, 2)}")',
            f'    Rel({first}, {second}, "uses")',
        ]
    )


def _mindmap(context: GenerationContext) -> str:
    return "\n".join(
        [
            "mindmap",
            f"  root(({_node(context)}))",
            f"    {_node(context)}",
            f"      {_node(context)}",
            f"    {_node(context)}",
        ]
    )


def _timeline(context: GenerationContext) -> str:
    return "\n".join(
        [
            "timeline",
            f"    title {_phrase(context, 4)}",
            f"    2024 : {_phrase(context, 2)}",
            f"    2025 : {_phrase(context, 3)}",
        ]
    )


def _zenuml(context: GenerationContext) -> str:
    return "\n".join(
        [
            "zenuml",
            f"    {_node(context)}->{_node(context)}: {context.text.word()}",
        ]
    )


def _sankey(context: GenerationContext) -> str:
    return "\n".join(
        [
            "sankey-beta",
            f"{_node(context)},{_node(context)},{context.text.number(5, 50)}",
            f"{_node(context)},{_node(context)},{context.text.number(5, 50)}",
        ]
    )


def _xy(context: GenerationContext) -> str:
    return "\n".join(
        [
            "xychart-beta",
            f"    title {_phrase(context, 3)}",
            "    x-axis [a, b, c]",
            "    y-axis 0 --> 10",
            "    bar [3, 6, 4]",
        ]
    )


def _block(context: GenerationContext) -> str:
    return "\n".join(
        [
            "block-beta",
            "    columns 2",
            f"    {_node(context)} {_node(context)}",
            f"    {_node(context)}",
        ]
    )


def _packet(context: GenerationContext) -> str:
    return "\n".join(
        [
            "packet-beta",
            '    0-15: "Source"',
            '    16-31: "Destination"',
            '    32-47: "Length"',
        ]
    )


def _kanban(context: GenerationContext) -> str:
    return "\n".join(
        [
            "kanban",
            "    todo[Todo]",
            f"        task1[{_phrase(context, 2)}]",
            "    done[Done]",
            f"        task2[{_phrase(context, 2)}]",
        ]
    )


def _architecture(context: GenerationContext) -> str:
    return "\n".join(
        [
            "architecture-beta",
            "    group api(cloud)[API]",
            f"    service web(server)[{_node(context)}] in api",
            f"    service db(database)[{_node(context)}] in api",
            "    web:R -- L:db",
        ]
    )


def _radar(context: GenerationContext) -> str:
    return "\n".join(
        [
            "radar-beta",
            "    axis a, b, c",
            f"    curve {_node(context)}{{3, 4, 5}}",
        ]
    )


def _eventmodeling(context: GenerationContext) -> str:
    return "\n".join(
        [
            "eventmodeling",
            f"    tf 1 {_node(context)}",
            f"    tf 2 {_node(context)}",
        ]
    )


def _treemap(context: GenerationContext) -> str:
    return "\n".join(
        [
            "treemap-beta",
            f'    "{_node(context)}"',
            f'        "{_node(context)}": 10',
            f'        "{_node(context)}": 6',
        ]
    )


def _venn(context: GenerationContext) -> str:
    return "\n".join(
        [
            "venn-beta",
            "    sets A, B",
            "    union A, B",
        ]
    )


def _ishikawa(context: GenerationContext) -> str:
    return "\n".join(
        [
            "ishikawa",
            f"    title {_phrase(context, 3)}",
            f"    {_node(context)}",
            f"        {_phrase(context, 2)}",
        ]
    )


def _wardley(context: GenerationContext) -> str:
    return "\n".join(
        [
            "wardley-beta",
            f"    title {_phrase(context, 3)}",
            f"    anchor {_node(context)} [0.5, 0.5]",
            f"    component {_node(context)} [0.6, 0.4]",
        ]
    )


def _treeview(context: GenerationContext) -> str:
    return "\n".join(
        [
            "treeView-beta",
            f"    {_node(context)}",
            f"        {_node(context)}",
            f"            {_node(context)}",
        ]
    )


def _usecase(context: GenerationContext) -> str:
    actor = _node(context)
    goal = _phrase(context, 4)
    return "\n".join(
        [
            "usecase-beta",
            f"    actor {actor}",
            f"    usecase {goal.replace(' ', '')}",
            f"    {actor} --> {goal.replace(' ', '')}",
        ]
    )


def _graphviz(context: GenerationContext) -> str:
    return "\n".join(
        [
            "digraph G {",
            f'    "{_node(context)}" -> "{_node(context)}";',
            "}",
        ]
    )


def _plantuml(context: GenerationContext) -> str:
    return "\n".join(
        [
            "@startuml",
            f"{_node(context)} -> {_node(context)} : {context.text.word()}",
            "@enduml",
        ]
    )


def _d2(context: GenerationContext) -> str:
    return "\n".join(
        [
            f"{_node(context)} -> {_node(context)}: {context.text.word()}",
        ]
    )


MERMAID_BODIES: dict[str, Callable[[GenerationContext], str]] = {
    "diagram.mermaid.flowchart": _flowchart,
    "diagram.mermaid.swimlane": _swimlane,
    "diagram.mermaid.sequence": _sequence,
    "diagram.mermaid.class": _class_diagram,
    "diagram.mermaid.state": _state,
    "diagram.mermaid.er": _er,
    "diagram.mermaid.gitgraph": _gitgraph,
    "diagram.mermaid.journey": _journey,
    "diagram.mermaid.gantt": _gantt,
    "diagram.mermaid.pie": _pie,
    "diagram.mermaid.quadrant": _quadrant,
    "diagram.mermaid.requirement": _requirement,
    "diagram.mermaid.c4": _c4,
    "diagram.mermaid.mindmap": _mindmap,
    "diagram.mermaid.timeline": _timeline,
    "diagram.mermaid.zenuml": _zenuml,
    "diagram.mermaid.sankey": _sankey,
    "diagram.mermaid.xy": _xy,
    "diagram.mermaid.block": _block,
    "diagram.mermaid.packet": _packet,
    "diagram.mermaid.kanban": _kanban,
    "diagram.mermaid.architecture": _architecture,
    "diagram.mermaid.radar": _radar,
    "diagram.mermaid.eventmodeling": _eventmodeling,
    "diagram.mermaid.treemap": _treemap,
    "diagram.mermaid.venn": _venn,
    "diagram.mermaid.ishikawa": _ishikawa,
    "diagram.mermaid.wardley": _wardley,
    "diagram.mermaid.treeview": _treeview,
    "diagram.mermaid.usecase": _usecase,
    "diagram.graphviz": _graphviz,
    "diagram.plantuml": _plantuml,
    "diagram.d2": _d2,
}

ENGINE_INFOS: dict[str, str] = {
    "diagram.graphviz": "graphviz",
    "diagram.plantuml": "plantuml",
    "diagram.d2": "d2",
}


@dataclass(frozen=True, slots=True)
class DiagramOptions:
    fence_info: str = "mermaid"

    def __post_init__(self) -> None:
        if not self.fence_info.strip():
            raise ValueError("diagram fence_info must not be empty")


class DiagramGenerator:
    family = "diagram"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, DiagramOptions(), DiagramOptions
        )
        features = [
            feature
            for feature in context.active_in_family("diagram")
            if feature in MERMAID_BODIES
        ]
        if not features:
            return CodeBlock(code=_flowchart(context), info=options.fence_info)
        chosen = context.weighted_feature(features)
        body = MERMAID_BODIES[chosen](context)
        info = ENGINE_INFOS.get(chosen, options.fence_info)
        return CodeBlock(code=body, info=info)


__all__ = [
    "DiagramGenerator",
    "DiagramOptions",
    "ENGINE_INFOS",
    "MERMAID_BODIES",
]
