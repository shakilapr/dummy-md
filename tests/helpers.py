"""Shared test helpers."""

from __future__ import annotations

from collections.abc import Mapping
from random import Random

from dummy_md import elements
from dummy_md.config import ElementRule
from dummy_md.core.budget import BudgetTracker
from dummy_md.core.context import GenerationContext
from dummy_md.core.dialects import get_dialect
from dummy_md.core.nodes import BlockNode, Document
from dummy_md.core.registry import Registry
from dummy_md.elements import build_generators
from dummy_md.text import TEXT_PROVIDERS, DummyContentEngine

REGISTRY = Registry()
elements.register(REGISTRY)


def build_context(
    *,
    dialect: str = "gfm",
    seed: int = 0,
    include: tuple[str, ...] = (),
    options: Mapping[str, ElementRule] | None = None,
    max_depth: int = 3,
    text_style: str = "pseudowords",
) -> GenerationContext:
    rng = Random(seed)
    selected = REGISTRY.resolve(dialect=dialect, include=list(include))
    return GenerationContext(
        rng=rng,
        dialect=get_dialect(dialect),
        text=DummyContentEngine(rng, TEXT_PROVIDERS[text_style]),
        active_features=selected,
        budget=BudgetTracker(unit="chars", target=10_000),
        options=options or {},
        max_depth=max_depth,
    )


def generate_block(family: str, **kwargs: object) -> BlockNode:
    context = build_context(**kwargs)  # type: ignore[arg-type]
    return build_generators()[family].generate(context)


def context_for_feature(feature_id: str, *, seed: int = 0) -> GenerationContext:
    """Context in the lowest dialect that supports ``feature_id``."""
    spec = REGISTRY.feature(feature_id)
    for name in ("commonmark", "gfm", "extended", "stress"):
        if name in spec.dialects:
            return build_context(dialect=name, seed=seed, include=(feature_id,))
    raise AssertionError(f"no dialect for {feature_id}")


def document_of(block: BlockNode) -> Document:
    return Document(children=(block,))
