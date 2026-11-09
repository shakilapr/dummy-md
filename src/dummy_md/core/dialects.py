"""Dialect capability sets, derived from the catalog."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from dummy_md.core.catalog import CATALOG
from dummy_md.core.features import DIALECT_ORDER, FeatureSpec
from dummy_md.exceptions import ConfigurationError, DialectError

_RENDERERS: dict[str, str] = {
    "commonmark": "commonmark",
    "gfm": "gfm",
    "extended": "gfm",
    "stress": "gfm",
}

_BASES: dict[str, str | None] = {
    "commonmark": None,
    "gfm": "commonmark",
    "extended": "gfm",
    "stress": "extended",
}


@dataclass(frozen=True, slots=True)
class Dialect:
    """A named, immutable capability set plus the renderer that emits it."""

    name: str
    renderer: str
    features: frozenset[str]
    base: str | None = None

    @property
    def rank(self) -> int:
        if self.name in DIALECT_ORDER:
            return DIALECT_ORDER.index(self.name)
        return len(DIALECT_ORDER)

    def supports(self, feature_id: str) -> bool:
        return feature_id in self.features


def _build() -> dict[str, Dialect]:
    built: dict[str, Dialect] = {}
    for name in DIALECT_ORDER:
        features = frozenset(
            spec.id for spec in CATALOG if spec.implemented and name in spec.dialects
        )
        built[name] = Dialect(
            name=name,
            renderer=_RENDERERS[name],
            features=features,
            base=_BASES[name],
        )
    return built


DIALECTS: dict[str, Dialect] = _build()


def get_dialect(name: str) -> Dialect:
    dialect = DIALECTS.get(name)
    if dialect is None:
        raise DialectError(f"unknown dialect {name!r}", dialects=DIALECT_ORDER)
    return dialect


def dialects_for(feature: FeatureSpec) -> tuple[str, ...]:
    return tuple(name for name in DIALECT_ORDER if name in feature.dialects)


def build_dialect(
    name: str,
    *,
    base: Dialect,
    features: Mapping[str, FeatureSpec],
    add: Iterable[str] = (),
    remove: Iterable[str] = (),
    renderer: str | None = None,
) -> Dialect:
    """Derive a custom dialect from ``base`` by adding or removing features.

    Addition is capability-level: a feature must be implemented, but it does not
    have to declare the new dialect in the catalog. Removal can strip any
    capability the base provides.
    """
    if not name:
        raise ConfigurationError("dialect name must not be empty")
    available = set(base.features)

    added: set[str] = set()
    for feature_id in add:
        spec = features.get(feature_id)
        if spec is None:
            raise ConfigurationError(
                f"cannot add unknown feature {feature_id!r} to dialect {name!r}"
            )
        if not spec.implemented:
            raise ConfigurationError(
                f"cannot add unimplemented feature {feature_id!r} to dialect {name!r}"
            )
        added.add(feature_id)

    removed: set[str] = set()
    for feature_id in remove:
        if feature_id not in available:
            raise ConfigurationError(
                f"cannot remove {feature_id!r} from dialect {name!r}: "
                "the base does not provide it"
            )
        removed.add(feature_id)

    overlap = added & removed
    if overlap:
        raise ConfigurationError(
            f"features cannot be added and removed at once: {sorted(overlap)}"
        )

    resolved = frozenset((available | added) - removed)
    if not resolved:
        raise ConfigurationError(f"dialect {name!r} would have no features")

    return Dialect(
        name=name,
        renderer=renderer or base.renderer,
        features=resolved,
        base=base.name,
    )
