"""Front-matter generation with metadata schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dummy_md.core.context import GenerationContext
from dummy_md.core.nodes import BlockNode, FrontMatter
from dummy_md.elements._util import resolve_options

_FORMATS: tuple[tuple[str, Literal["yaml", "toml", "json"]], ...] = (
    ("frontmatter.yaml", "yaml"),
    ("frontmatter.toml", "toml"),
    ("frontmatter.json", "json"),
)
Scalar = str | int | bool
Field = tuple[str, Scalar | list[str] | dict[str, Scalar]]

_META_FIELDS: tuple[str, ...] = (
    "meta.title",
    "meta.subtitle",
    "meta.author",
    "meta.dates",
    "meta.abstract",
    "meta.description",
    "meta.tags",
    "meta.categories",
    "meta.aliases",
    "meta.draft",
    "meta.slug",
    "meta.permalink",
    "meta.language",
    "meta.toc",
    "meta.output_format",
    "meta.custom",
    "meta.nested",
)


@dataclass(frozen=True, slots=True)
class FrontMatterOptions:
    max_fields: int = 8

    def __post_init__(self) -> None:
        if self.max_fields < 1:
            raise ValueError("max_fields must be at least 1")


class FrontMatterGenerator:
    family = "frontmatter"

    def generate(self, context: GenerationContext) -> BlockNode:
        options = resolve_options(
            context, self.family, FrontMatterOptions(), FrontMatterOptions
        )
        fmt = self._format(context)
        fields = self._fields(context, options)
        return FrontMatter(format=fmt, content=self._render(fmt, fields))

    # -- selection --------------------------------------------------------
    def _format(self, context: GenerationContext) -> Literal["yaml", "toml", "json"]:
        if any(
            feature.startswith("platform.obsidian.property.")
            or feature.startswith("citation.bibliography_")
            for feature in context.active_features
        ):
            # Platform metadata and bibliography keys are emitted as YAML, so a
            # single mergeable metadata block is possible.
            return "yaml"
        choices: list[Literal["yaml", "toml", "json"]] = [
            fmt for feature, fmt in _FORMATS if context.supports(feature)
        ]
        if not choices:
            return "yaml"
        return context.rng.choice(choices)

    def _fields(
        self, context: GenerationContext, options: FrontMatterOptions
    ) -> list[Field]:
        builders: dict[str, Field] = {
            "meta.title": (
                "title",
                context.text.phrase(min_words=2, max_words=5, title_case=True),
            ),
            "meta.subtitle": (
                "subtitle",
                context.text.phrase(min_words=3, max_words=7, title_case=True),
            ),
            "meta.author": (
                "author",
                f"{context.text.word().title()} {context.text.word().title()}",
            ),
            "meta.dates": ("date", context.text.date()),
            "meta.abstract": (
                "abstract",
                context.text.sentence(min_words=8, max_words=16),
            ),
            "meta.description": (
                "description",
                context.text.sentence(min_words=6, max_words=12),
            ),
            "meta.tags": ("tags", [context.text.word(), context.text.word()]),
            "meta.categories": ("categories", [context.text.word()]),
            "meta.aliases": ("aliases", [context.text.slug()]),
            "meta.draft": ("draft", context.rng.random() < 0.3),
            "meta.slug": ("slug", context.text.slug()),
            "meta.permalink": ("permalink", "/" + context.text.slug() + "/"),
            "meta.language": ("lang", "en"),
            "meta.toc": ("toc", True),
            "meta.output_format": ("format", "html"),
            "meta.custom": ("x-" + context.text.word(), context.text.word()),
            "meta.nested": (
                "build",
                {"target": context.text.word(), "minify": True},
            ),
        }
        fields = [
            builders[feature] for feature in _META_FIELDS if context.supports(feature)
        ]
        if len(fields) > options.max_fields:
            fields = fields[: options.max_fields]
        if not fields:
            fields = [builders["meta.title"]]
        return fields

    # -- serialization ----------------------------------------------------
    def _render(self, fmt: str, fields: list[Field]) -> str:
        if fmt == "json":
            return self._json(fields)
        if fmt == "toml":
            return self._toml(fields)
        return self._yaml(fields)

    def _yaml(self, fields: list[Field], indent: int = 0) -> str:
        pad = "  " * indent
        lines: list[str] = []
        for key, value in fields:
            if isinstance(value, dict):
                lines.append(f"{pad}{key}:")
                lines.append(self._yaml(list(value.items()), indent + 1))
            elif isinstance(value, list):
                lines.append(f"{pad}{key}:")
                lines.extend(f"{pad}  - {item}" for item in value)
            elif isinstance(value, bool):
                lines.append(f"{pad}{key}: {str(value).lower()}")
            else:
                lines.append(f"{pad}{key}: {value}")
        return "\n".join(lines)

    def _toml(self, fields: list[Field]) -> str:
        lines: list[str] = []
        for key, value in fields:
            if isinstance(value, dict):
                lines.append(f"[{key}]")
                for inner_key, inner_value in value.items():
                    lines.append(f"{inner_key} = {self._toml_value(inner_value)}")
                lines.append("")
            else:
                lines.append(f"{key} = {self._toml_value(value)}")
        return "\n".join(lines).rstrip("\n")

    @staticmethod
    def _toml_value(value: Scalar | list[str]) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, list):
            rendered = ", ".join(f'"{item}"' for item in value)
            return f"[{rendered}]"
        if isinstance(value, int):
            return str(value)
        return f'"{value}"'

    def _json(self, fields: list[Field]) -> str:
        lines = ["{"]
        entries: list[str] = []
        for key, value in fields:
            entries.append(f'  "{key}": {self._json_value(value)}')
        lines.append(",\n".join(entries))
        lines.append("}")
        return "\n".join(lines)

    def _json_value(self, value: Scalar | list[str] | dict[str, Scalar]) -> str:
        if isinstance(value, dict):
            inner = ", ".join(f'"{k}": {self._json_value(v)}' for k, v in value.items())
            return "{" + inner + "}"
        if isinstance(value, list):
            return "[" + ", ".join(f'"{item}"' for item in value) + "]"
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, int):
            return str(value)
        return f'"{value}"'
