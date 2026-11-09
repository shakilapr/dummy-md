"""Display math, LaTeX environments, and math code fences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, CodeBlock, MathBlock, MathMacros
from dummy_md.elements._util import resolve_options
from dummy_md.elements.payloads import MATH_ENVIRONMENTS, MATH_PAYLOADS


@dataclass(frozen=True, slots=True)
class MathOptions:
    fence_ratio: float = 0.3
    environment_ratio: float = 0.6
    payload_ratio: float = 0.8
    delimiter: Literal["dollar", "bracket", "random"] = "random"
    label_ratio: float = 0.5
    macro_ratio: float = 0.15


class MathGenerator:
    family = "math"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(context, self.family, MathOptions(), MathOptions)
        features = context.active_in_family("math")
        if (
            context.supports("math.macros")
            and context.rng.random() < options.macro_ratio
        ):
            return MathMacros(
                definitions=tuple(
                    (
                        context.text.word(min_length=2, max_length=4),
                        "\\" + context.text.word(min_length=2, max_length=4),
                    )
                    for _ in range(context.text.number(1, 3))
                )
            )
        expression = self._expression(context, features, options)
        label = ""
        if (
            context.supports("math.label")
            and context.rng.random() < options.label_ratio
        ):
            label = "eq:" + context.text.slug()

        if "math.fence" in features and context.rng.random() < options.fence_ratio:
            return CodeBlock(code=expression, info="math")

        environments = [feature for feature in MATH_ENVIRONMENTS if feature in features]
        if environments and context.rng.random() < options.environment_ratio:
            feature = context.weighted_feature(environments)
            environment = MATH_ENVIRONMENTS[feature]
            return MathBlock(
                expression=self._environment_body(context, environment, expression),
                environment=environment,
                label=label,
            )

        return MathBlock(
            expression=expression,
            delimiter=self._delimiter(context, features, options),
            label=label,
        )

    # -- helpers ----------------------------------------------------------
    def _expression(
        self,
        context: GenerationContext,
        features: tuple[str, ...],
        options: MathOptions,
    ) -> str:
        payloads = [feature for feature in MATH_PAYLOADS if feature in features]
        if payloads and context.rng.random() < options.payload_ratio:
            return MATH_PAYLOADS[context.weighted_feature(payloads)](context)
        return "x + y = z"

    def _delimiter(
        self,
        context: GenerationContext,
        features: tuple[str, ...],
        options: MathOptions,
    ) -> Literal["dollar", "bracket"]:
        if options.delimiter != "random":
            return options.delimiter
        candidates = [
            feature
            for feature in ("math.display.dollar", "math.display.bracket")
            if feature in features
        ]
        if not candidates:
            return "dollar"
        chosen = context.weighted_feature(candidates)
        return "dollar" if chosen.endswith("dollar") else "bracket"

    def _environment_body(
        self, context: GenerationContext, environment: str, expression: str
    ) -> str:
        if environment == "align":
            return " \\\\\n".join(
                f"{context.text.word()}_{{{index}}} &= {expression}"
                for index in range(1, context.text.number(2, 4))
            )
        if environment == "gather":
            return " \\\\\n".join(
                f"{expression} + {context.text.number(1, 9)}" for _ in range(2)
            )
        if environment == "cases":
            return "\n".join(
                [
                    f"{expression} & x > {context.text.number(0, 9)} \\\\",
                    f"{context.text.word()} & \\text{{otherwise}}",
                ]
            )
        if environment == "matrix":
            return "\n".join(
                [
                    f"{context.text.number(1, 9)} & {context.text.number(1, 9)} \\\\",
                    f"{context.text.number(1, 9)} & {context.text.number(1, 9)}",
                ]
            )
        return expression
