from __future__ import annotations

import pytest

from dummy_md.core.catalog import CATALOG, IMPLEMENTED_IDS
from dummy_md.core.dialects import DIALECTS, Dialect, dialects_for, get_dialect
from dummy_md.core.features import (
    KINDS,
    TIERS,
    FeatureSpec,
    group_by_generator,
    resolve,
    resolve_for,
    validate_catalog,
)
from dummy_md.core.registry import Registry
from dummy_md.exceptions import ConfigurationError, DialectError

FEATURES = {spec.id: spec for spec in CATALOG}


def test_catalog_covers_research_inventory() -> None:
    assert len(CATALOG) >= 420


def test_catalog_invariants_hold() -> None:
    validate_catalog(FEATURES)


def test_feature_ids_unique() -> None:
    ids = [spec.id for spec in CATALOG]
    assert len(ids) == len(set(ids))


def test_kinds_and_tiers_are_known() -> None:
    assert {spec.kind for spec in CATALOG} <= KINDS
    assert {spec.tier for spec in CATALOG} <= set(TIERS)


def test_every_family_has_a_generator_or_is_implicit() -> None:
    for spec in CATALOG:
        if spec.implemented and spec.id not in {"doc.body", "stress.document.large"}:
            assert spec.generator is not None, spec.id


def test_implemented_ids_are_sorted_and_nonempty() -> None:
    assert IMPLEMENTED_IDS == tuple(sorted(IMPLEMENTED_IDS))
    assert len(IMPLEMENTED_IDS) > 100


def test_dialects_are_derived_from_catalog() -> None:
    for name, dialect in DIALECTS.items():
        for feature_id in dialect.features:
            assert name in FEATURES[feature_id].dialects
            assert FEATURES[feature_id].implemented


def test_commonmark_excludes_gfm_tables() -> None:
    assert "table.pipe" not in get_dialect("commonmark").features
    assert "table.pipe" in get_dialect("gfm").features


def test_extended_adds_math_but_gfm_does_not() -> None:
    assert "math.inline.dollar" not in get_dialect("gfm").features
    assert "math.inline.dollar" in get_dialect("extended").features


def test_unknown_dialect_raises() -> None:
    with pytest.raises(DialectError, match="unknown dialect"):
        get_dialect("markdown-extra")


def test_default_resolution_is_dialect_legal() -> None:
    selected = resolve(FEATURES, dialect="gfm")
    assert "heading.atx.h1" in selected
    assert "table.pipe" in selected
    assert "math.inline.dollar" not in selected


def test_glob_selection_filters_by_dialect() -> None:
    selected = resolve(FEATURES, dialect="gfm", include=["table.*"])
    assert "table.pipe" in selected
    assert "table.caption" not in selected


def test_exact_feature_outside_dialect_errors() -> None:
    with pytest.raises(DialectError) as excinfo:
        resolve(FEATURES, dialect="commonmark", include=["table.pipe"])
    assert excinfo.value.dialects == ("gfm", "extended", "stress")


def test_unknown_pattern_errors() -> None:
    with pytest.raises(ConfigurationError, match="matches no known feature"):
        resolve(FEATURES, dialect="gfm", include=["heading.nope"])


def test_unimplemented_pattern_errors() -> None:
    with pytest.raises(ConfigurationError, match="unimplemented"):
        resolve(FEATURES, dialect="stress", include=["stress.document.large"])


def test_exclude_wins_over_include() -> None:
    selected = resolve(
        FEATURES, dialect="gfm", include=["heading.*"], exclude=["heading.setext.*"]
    )
    assert "heading.atx.h1" in selected
    assert "heading.setext.h1" not in selected


def _extended_with(*extra: str) -> Dialect:
    base = get_dialect("extended")
    return Dialect(
        name="probe",
        renderer=base.renderer,
        features=frozenset(set(base.features) | set(extra)),
        base=base.name,
    )


def test_requires_closure_is_pulled_in() -> None:
    features = dict(FEATURES)
    features["table.grid.colspan"] = FeatureSpec(
        id="table.grid.colspan",
        family="table",
        kind="structure",
        dialects=features["table.grid.colspan"].dialects,
        tier="extended",
        generator="table",
        requires=frozenset({"table.grid"}),
        implemented=True,
    )
    features["table.grid"] = FeatureSpec(
        id="table.grid",
        family="table",
        kind="structure",
        dialects=features["table.grid"].dialects,
        tier="extended",
        generator="table",
        implemented=True,
    )
    dialect = _extended_with("table.grid", "table.grid.colspan")
    selected = resolve_for(features, dialect=dialect, include=["table.grid.colspan"])
    assert selected == {"table.grid", "table.grid.colspan"}


def test_requires_with_excluded_prerequisite_errors() -> None:
    features = dict(FEATURES)
    features["table.grid"] = FeatureSpec(
        id="table.grid",
        family="table",
        kind="structure",
        dialects=features["table.grid"].dialects,
        tier="extended",
        generator="table",
        implemented=True,
    )
    features["table.grid.rowspan"] = FeatureSpec(
        id="table.grid.rowspan",
        family="table",
        kind="structure",
        dialects=features["table.grid.rowspan"].dialects,
        tier="extended",
        generator="table",
        requires=frozenset({"table.grid"}),
        implemented=True,
    )
    dialect = _extended_with("table.grid", "table.grid.rowspan")
    with pytest.raises(ConfigurationError, match="requires"):
        resolve_for(
            features,
            dialect=dialect,
            include=["table.grid.rowspan"],
            exclude=["table.grid"],
        )


def test_cyclic_requirements_are_rejected() -> None:
    cycle = {
        "a.one": FeatureSpec(
            id="a.one",
            family="a",
            kind="structure",
            dialects=frozenset({"gfm"}),
            tier="core",
            generator="heading",
            requires=frozenset({"a.two"}),
        ),
        "a.two": FeatureSpec(
            id="a.two",
            family="a",
            kind="structure",
            dialects=frozenset({"gfm"}),
            tier="core",
            generator="heading",
            requires=frozenset({"a.one"}),
        ),
    }
    with pytest.raises(ConfigurationError, match="cyclic"):
        validate_catalog(cycle)


def test_group_by_generator_orders_ids() -> None:
    selected = resolve(FEATURES, dialect="gfm", include=["heading.*", "table.pipe"])
    grouped = group_by_generator(FEATURES, selected)
    assert grouped["heading"] == tuple(sorted(grouped["heading"]))
    assert "table" in grouped
    assert grouped["table"] == ("table.pipe",)


def test_registry_resolves_and_schedules() -> None:
    registry = Registry()
    selected = registry.resolve(dialect="commonmark", include=["heading.atx.h1"])
    assert selected == frozenset({"heading.atx.h1"})
    assert registry.dialect_names() == ("commonmark", "gfm", "extended", "stress")


def test_registry_rejects_duplicate_feature() -> None:
    registry = Registry()
    with pytest.raises(ConfigurationError, match="already registered"):
        registry.register_feature(FEATURES["heading.atx.h1"])


def test_dialects_for_reports_ordered_names() -> None:
    assert dialects_for(FEATURES["table.pipe"]) == ("gfm", "extended", "stress")
    assert dialects_for(FEATURES["heading.atx.h1"]) == (
        "commonmark",
        "gfm",
        "extended",
        "stress",
    )
