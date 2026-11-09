"""Central registry for features, generators, payloads, and dialects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from dummy_md.core.catalog import CATALOG
from dummy_md.core.dialects import DIALECTS, Dialect, get_dialect
from dummy_md.core.features import (
    FeatureSpec,
    group_by_generator,
    resolve,
    validate_catalog,
)
from dummy_md.core.nodes import BlockNode
from dummy_md.exceptions import ConfigurationError

if TYPE_CHECKING:
    from dummy_md.core.context import GenerationContext


@runtime_checkable
class ElementGenerator(Protocol):
    """A family-level block producer."""

    @property
    def family(self) -> str: ...

    def generate(self, context: GenerationContext) -> BlockNode: ...


@runtime_checkable
class PayloadProvider(Protocol):
    """Body-text provider for payload features (code, math, diagrams, metadata)."""

    @property
    def payload_ids(self) -> frozenset[str]: ...

    def render(self, context: GenerationContext) -> str: ...


class Registry:
    """Mutable registry with explicit, conflict-checked registration."""

    def __init__(self, features: Iterable[FeatureSpec] = CATALOG) -> None:
        self._features: dict[str, FeatureSpec] = {}
        self._generators: dict[str, ElementGenerator] = {}
        self._payloads: dict[str, PayloadProvider] = {}
        self._dialects: dict[str, Dialect] = dict(DIALECTS)
        for spec in features:
            self._features[spec.id] = spec

    # -- features ---------------------------------------------------------
    @property
    def features(self) -> Mapping[str, FeatureSpec]:
        return self._features

    def feature(self, feature_id: str) -> FeatureSpec:
        spec = self._features.get(feature_id)
        if spec is None:
            raise ConfigurationError(f"unknown feature {feature_id!r}")
        return spec

    def register_feature(self, spec: FeatureSpec, *, replace: bool = False) -> None:
        if spec.id in self._features and not replace:
            raise ConfigurationError(f"feature {spec.id!r} is already registered")
        self._features[spec.id] = spec

    def validate(self) -> None:
        validate_catalog(self._features)
        for spec in self._features.values():
            if (
                spec.implemented
                and spec.generator
                and spec.generator not in self._generators
            ):
                raise ConfigurationError(
                    f"implemented feature {spec.id!r} needs generator "
                    f"{spec.generator!r}, which is not registered"
                )

    # -- generators -------------------------------------------------------
    def register_generator(
        self, generator: ElementGenerator, *, replace: bool = False
    ) -> None:
        family = generator.family
        if family in self._generators and not replace:
            raise ConfigurationError(f"generator for {family!r} is already registered")
        known = {spec.generator for spec in self._features.values()}
        if family not in known:
            raise ConfigurationError(
                f"generator {family!r} has no catalog features; add features first"
            )
        self._generators[family] = generator

    def generator(self, family: str) -> ElementGenerator:
        try:
            return self._generators[family]
        except KeyError:
            raise ConfigurationError(
                f"no generator registered for {family!r}"
            ) from None

    def generator_families(self) -> tuple[str, ...]:
        return tuple(sorted(self._generators))

    # -- payloads ---------------------------------------------------------
    def register_payload(self, payload: PayloadProvider) -> None:
        for payload_id in payload.payload_ids:
            if payload_id in self._payloads:
                raise ConfigurationError(
                    f"payload {payload_id!r} is already registered"
                )
            self._payloads[payload_id] = payload

    # -- dialects ---------------------------------------------------------
    def dialect(self, name: str) -> Dialect:
        return get_dialect(name)

    def dialect_names(self) -> tuple[str, ...]:
        return tuple(dialect.name for dialect in self._dialects.values())

    # -- selection --------------------------------------------------------
    def resolve(
        self,
        *,
        dialect: str,
        include: Sequence[str] = (),
        exclude: Sequence[str] = (),
    ) -> frozenset[str]:
        selected = resolve(
            self._features, dialect=dialect, include=include, exclude=exclude
        )
        self.dialect(dialect)
        return selected

    def schedule(self, selected: Iterable[str]) -> dict[str, tuple[str, ...]]:
        """Map selected features onto registered generator families."""
        grouped = group_by_generator(self._features, selected)
        missing = sorted(set(grouped) - set(self._generators))
        if missing:
            raise ConfigurationError(
                "selected features need unregistered generators: " + ", ".join(missing)
            )
        return grouped


registry = Registry()
