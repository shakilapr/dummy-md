"""Display math, LaTeX environments, and math code fences."""

from __future__ import annotations

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, CodeBlock, MathBlock
from dummy_md.elements.payloads import MATH_ENVIRONMENTS, MATH_PAYLOADS


class MathGenerator:
    family = "math"

    def generate(self, context: GenerationContext) -> BlockNode:
        features = context.active_in_family("math")
        expression = self._expression(context, features)

        if "math.fence" in features and context.rng.random() < 0.3:
            return CodeBlock(code=expression, info="math")

        for feature, environment in MATH_ENVIRONMENTS.items():
            if feature in features:
                return MathBlock(
                    expression=self._environment_body(context, environment, expression),
                    environment=environment,
                )

        delimiter = "bracket" if "math.display.bracket" in features else "dollar"
        if (
            "math.display.dollar" not in features
            and "math.display.bracket" not in features
        ):
            delimiter = "dollar"
        return MathBlock(expression=expression, delimiter=delimiter)  # type: ignore[arg-type]

    # -- helpers ----------------------------------------------------------
    def _expression(self, context: GenerationContext, features: tuple[str, ...]) -> str:
        builders = [
            build for feature, build in MATH_PAYLOADS.items() if feature in features
        ]
        if builders:
            return context.rng.choice(builders)(context)
        return self._environment_body(context, "equation", "x + y = z")

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
