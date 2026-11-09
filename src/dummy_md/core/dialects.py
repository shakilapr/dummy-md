"""Dialect capability sets, derived from the catalog."""

from __future__ import annotations

from dataclasses import dataclass

from dummy_md.core.catalog import CATALOG
from dummy_md.core.features import DIALECT_ORDER, FeatureSpec
from dummy_md.exceptions import DialectError

_RENDERERS: dict[str, str] = {
    "commonmark": "commonmark",
    "gfm": "gfm",
    "extended": "gfm",
    "stress": "gfm",
}


@dataclass(frozen=True, slots=True)
class Dialect:
    """A named, immutable capability set."""

    name: str
    renderer: str
    features: frozenset[str]

    @property
    def rank(self) -> int:
        return DIALECT_ORDER.index(self.name)

    def supports(self, feature_id: str) -> bool:
        return feature_id in self.features


def _build() -> dict[str, Dialect]:
    built: dict[str, Dialect] = {}
    for name in DIALECT_ORDER:
        features = frozenset(
            spec.id for spec in CATALOG if spec.implemented and name in spec.dialects
        )
        built[name] = Dialect(name=name, renderer=_RENDERERS[name], features=features)
    return built


DIALECTS: dict[str, Dialect] = _build()


def get_dialect(name: str) -> Dialect:
    dialect = DIALECTS.get(name)
    if dialect is None:
        raise DialectError(f"unknown dialect {name!r}", dialects=DIALECT_ORDER)
    return dialect


def dialects_for(feature: FeatureSpec) -> tuple[str, ...]:
    return tuple(name for name in DIALECT_ORDER if name in feature.dialects)
