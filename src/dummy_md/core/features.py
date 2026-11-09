"""Feature model: catalog entries, glob selection, and capability resolution."""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from dummy_md.exceptions import ConfigurationError, DialectError

DIALECT_ORDER: tuple[str, ...] = ("commonmark", "gfm", "extended", "stress")
KINDS: frozenset[str] = frozenset(
    {"structure", "syntax_variant", "payload", "metadata", "stress"}
)
TIERS: tuple[str, ...] = ("core", "extended", "platform", "advanced")

_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*$")


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """One addressable generation target."""

    id: str
    family: str
    kind: str
    dialects: frozenset[str]
    tier: str
    generator: str | None = None
    requires: frozenset[str] = frozenset()
    default_weight: float = 1.0
    implemented: bool = False
    options: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({}), compare=True, hash=False
    )

    def __post_init__(self) -> None:
        if not _ID_RE.match(self.id):
            raise ConfigurationError(f"invalid feature id {self.id!r}")
        if self.family != self.id.split(".")[0]:
            raise ConfigurationError(
                f"feature {self.id!r} declares family {self.family!r}"
            )
        if self.kind not in KINDS:
            raise ConfigurationError(
                f"feature {self.id!r} has unknown kind {self.kind!r}"
            )
        if self.tier not in TIERS:
            raise ConfigurationError(
                f"feature {self.id!r} has unknown tier {self.tier!r}"
            )
        if not self.dialects:
            raise ConfigurationError(f"feature {self.id!r} has no dialects")
        unknown = sorted(set(self.dialects) - set(DIALECT_ORDER))
        if unknown:
            raise ConfigurationError(
                f"feature {self.id!r} references unknown dialects {unknown}"
            )
        if self.default_weight <= 0:
            raise ConfigurationError(f"feature {self.id!r} must have a positive weight")
        for required in self.requires:
            if not _ID_RE.match(required):
                raise ConfigurationError(
                    f"feature {self.id!r} requires malformed id {required!r}"
                )

    @property
    def tier_rank(self) -> int:
        return TIERS.index(self.tier)

    def matches(self, pattern: str) -> bool:
        return self.id == pattern or fnmatch.fnmatchcase(self.id, pattern)


def _expand(
    features: Mapping[str, FeatureSpec],
    pattern: str,
    *,
    dialect: str,
    role: str,
) -> list[FeatureSpec]:
    matched = sorted(
        (spec for spec in features.values() if spec.matches(pattern)),
        key=lambda spec: spec.id,
    )
    if not matched:
        raise ConfigurationError(
            f"{role} pattern {pattern!r} matches no known feature id"
        )

    implemented = [spec for spec in matched if spec.implemented]
    if not implemented:
        ids = ", ".join(spec.id for spec in matched)
        raise ConfigurationError(
            f"{role} pattern {pattern!r} only matches unimplemented features: {ids}"
        )

    is_glob = any(character in pattern for character in "*?[")
    if is_glob:
        # Dialect filtering is expected for globs: `table.*` keeps what GFM can emit.
        legal = [spec for spec in implemented if dialect in spec.dialects]
        if not legal:
            raise DialectError(
                f"{role} pattern {pattern!r} has no feature available in {dialect!r}",
                dialects=_dialects_of(implemented),
            )
        return legal

    spec = implemented[0]
    if dialect not in spec.dialects:
        raise DialectError(
            f"feature {spec.id!r} is not available in dialect {dialect!r}",
            dialects=_dialects_of((spec,)),
        )
    return [spec]


def _dialects_of(specs: Iterable[FeatureSpec]) -> tuple[str, ...]:
    names: set[str] = set()
    for spec in specs:
        names |= set(spec.dialects)
    return tuple(name for name in DIALECT_ORDER if name in names)


def resolve(
    features: Mapping[str, FeatureSpec],
    *,
    dialect: str,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
) -> frozenset[str]:
    """Resolve include/exclude patterns into a legal feature set for ``dialect``."""
    if dialect not in DIALECT_ORDER:
        raise DialectError(f"unknown dialect {dialect!r}", dialects=DIALECT_ORDER)

    available = {
        spec.id
        for spec in features.values()
        if spec.implemented and dialect in spec.dialects
    }

    if include:
        selected: set[str] = set()
        for pattern in include:
            selected |= {
                spec.id
                for spec in _expand(features, pattern, dialect=dialect, role="include")
            }
    else:
        selected = set(available)

    excluded: set[str] = set()
    for pattern in exclude:
        excluded |= {
            spec.id
            for spec in _expand(features, pattern, dialect=dialect, role="exclude")
        }

    selected -= excluded

    # Pull in prerequisites, rejecting features that already excluded them.
    pending = sorted(selected)
    while pending:
        current = pending.pop()
        spec = features[current]
        if dialect not in spec.dialects:
            raise DialectError(
                f"feature {current!r} is not available in dialect {dialect!r}",
                dialects=_dialects_of((spec,)),
            )
        for required in sorted(spec.requires):
            if required in excluded:
                raise ConfigurationError(
                    f"feature {current!r} requires {required!r}, which was excluded"
                )
            required_spec = features.get(required)
            if required_spec is None:
                raise ConfigurationError(
                    f"feature {current!r} requires unknown feature {required!r}"
                )
            if not required_spec.implemented:
                raise ConfigurationError(
                    f"feature {current!r} requires unimplemented feature {required!r}"
                )
            if required not in selected:
                selected.add(required)
                pending.append(required)

    if not selected:
        raise ConfigurationError("feature selection resolved to an empty set")

    return frozenset(selected)


def validate_catalog(features: Mapping[str, FeatureSpec]) -> None:
    """Check the catalog invariants that data alone cannot express."""
    seen: set[str] = set()
    for spec_id, spec in features.items():
        if spec_id != spec.id:
            raise ConfigurationError(
                f"catalog key {spec_id!r} does not match id {spec.id!r}"
            )
        if spec.id in seen:
            raise ConfigurationError(f"duplicate feature id {spec.id!r}")
        seen.add(spec.id)

    for spec in features.values():
        for required in spec.requires:
            target = features.get(required)
            if target is None:
                raise ConfigurationError(
                    f"feature {spec.id!r} requires unknown feature {required!r}"
                )
            missing = set(target.dialects) - set(spec.dialects)
            if missing:
                raise ConfigurationError(
                    f"feature {spec.id!r} requires {required!r}, which supports "
                    f"dialects not available to the requirement: {sorted(missing)}"
                )
            if not target.implemented and spec.implemented:
                raise ConfigurationError(
                    f"implemented feature {spec.id!r} requires "
                    f"unimplemented {required!r}"
                )

    # Cycle detection over the requires graph.
    state: dict[str, int] = {}
    for spec in features.values():
        _visit(spec.id, features, state)


def _visit(
    spec_id: str, features: Mapping[str, FeatureSpec], state: dict[str, int]
) -> None:
    mark = state.get(spec_id, 0)
    if mark == 1:
        raise ConfigurationError(f"cyclic feature requirement involving {spec_id!r}")
    if mark == 2:
        return
    state[spec_id] = 1
    for required in features[spec_id].requires:
        _visit(required, features, state)
    state[spec_id] = 2


def group_by_generator(
    features: Mapping[str, FeatureSpec], selected: Iterable[str]
) -> dict[str, tuple[str, ...]]:
    """Group a resolved feature set by the generator that produces it."""
    grouped: dict[str, list[str]] = {}
    for spec_id in sorted(selected):
        generator = features[spec_id].generator
        if generator is None:
            continue
        grouped.setdefault(generator, []).append(spec_id)
    return {generator: tuple(ids) for generator, ids in grouped.items()}
