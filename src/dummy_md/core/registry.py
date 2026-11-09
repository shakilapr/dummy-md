"""Central registry for features, generators, renderers, payloads, and dialects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from dummy_md.core.catalog import CATALOG
from dummy_md.core.dialects import DIALECTS, Dialect, build_dialect
from dummy_md.core.features import (
    FeatureSpec,
    group_by_generator,
    resolve_for,
    validate_catalog,
)
from dummy_md.core.nodes import BlockNode
from dummy_md.exceptions import ConfigurationError, DialectError
from dummy_md.renderers import RENDERERS
from dummy_md.renderers.base import BaseRenderer

if TYPE_CHECKING:
    from dummy_md.core.context import GenerationContext

RendererFactory = type[BaseRenderer]


@runtime_checkable
class ElementGenerator(Protocol):
    """A family-level block producer."""

    @property
    def family(self) -> str: ...

    def generate(self, context: GenerationContext) -> BlockNode: ...


class Registry:
    """Mutable registry with explicit, conflict-checked registration."""

    def __init__(
        self,
        features: Iterable[FeatureSpec] = CATALOG,
        *,
        renderers: Mapping[str, RendererFactory] | None = None,
        dialects: Mapping[str, Dialect] | None = None,
    ) -> None:
        self._features: dict[str, FeatureSpec] = {}
        self._generators: dict[str, ElementGenerator] = {}
        self._renderers: dict[str, RendererFactory] = dict(
            RENDERERS if renderers is None else renderers
        )
        self._dialects: dict[str, Dialect] = dict(
            DIALECTS if dialects is None else dialects
        )
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
        for dialect in self._dialects.values():
            if dialect.renderer not in self._renderers:
                raise ConfigurationError(
                    f"dialect {dialect.name!r} needs renderer "
                    f"{dialect.renderer!r}, which is not registered"
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

    # -- renderers --------------------------------------------------------
    def register_renderer(
        self, name: str, renderer: RendererFactory, *, replace: bool = False
    ) -> None:
        if name in self._renderers and not replace:
            raise ConfigurationError(f"renderer {name!r} is already registered")
        self._renderers[name] = renderer

    def renderer(self, name: str) -> RendererFactory:
        try:
            return self._renderers[name]
        except KeyError:
            raise ConfigurationError(f"no renderer registered for {name!r}") from None

    def renderer_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._renderers))

    # -- dialects ---------------------------------------------------------
    def dialect(self, name: str) -> Dialect:
        dialect = self._dialects.get(name)
        if dialect is None:
            raise DialectError(
                f"unknown dialect {name!r}", dialects=tuple(sorted(self._dialects))
            )
        return dialect

    def register_dialect(self, dialect: Dialect, *, replace: bool = False) -> None:
        if dialect.name in self._dialects and not replace:
            raise ConfigurationError(f"dialect {dialect.name!r} is already registered")
        if dialect.renderer not in self._renderers:
            raise ConfigurationError(
                f"dialect {dialect.name!r} needs unregistered renderer "
                f"{dialect.renderer!r}"
            )
        self._dialects[dialect.name] = dialect

    def add_dialect(
        self,
        name: str,
        *,
        base: str = "gfm",
        add: Iterable[str] = (),
        remove: Iterable[str] = (),
        renderer: str | None = None,
        replace: bool = False,
    ) -> Dialect:
        """Create a dialect by adding/removing capabilities of an existing one."""
        if name in self._dialects and not replace:
            raise ConfigurationError(f"dialect {name!r} is already registered")
        derived = build_dialect(
            name,
            base=self.dialect(base),
            features=self._features,
            add=add,
            remove=remove,
            renderer=renderer,
        )
        self.register_dialect(derived, replace=replace)
        return derived

    def dialect_names(self) -> tuple[str, ...]:
        return tuple(self._dialects)

    # -- selection --------------------------------------------------------
    def resolve(
        self,
        *,
        dialect: str,
        include: Sequence[str] = (),
        exclude: Sequence[str] = (),
    ) -> frozenset[str]:
        resolved = self.dialect(dialect)
        return resolve_for(
            self._features, dialect=resolved, include=include, exclude=exclude
        )

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
