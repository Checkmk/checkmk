#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._explicit_graphs import ExplicitGraphSpecification
from cmk.gui.graphing._graph_specification import FixedVerticalRange
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.unit_formatter import AutoPrecision

_UNIT = ConvertibleUnitSpecification(
    notation=DecimalNotation(symbol=""),
    precision=AutoPrecision(digits=2),
)


def _specification() -> ExplicitGraphSpecification:
    return ExplicitGraphSpecification(
        title="Forecast: heute - CPU load",
        unit=_UNIT,
        consolidation_function="max",
        explicit_vertical_range=(10.0, 20.0),
        omit_zero_metrics=False,
        horizontal_rules=[],
        metrics=[],
        mark_requested_end_time=True,
    )


def test_the_recipe_carries_the_specifications_own_fields() -> None:
    # The forecast element of a report renders through this recipe, because the engine has no
    # counterpart for the ad hoc forecast transformation it builds.
    (recipe_with_overrides,) = _specification().recipes(None, [])  # type: ignore[arg-type]

    assert recipe_with_overrides.recipe.title == "Forecast: heute - CPU load"
    assert recipe_with_overrides.recipe.explicit_vertical_range == FixedVerticalRange(
        min=10.0, max=20.0
    )
    assert recipe_with_overrides.consolidation_function == "max"
    assert recipe_with_overrides.mark_requested_end_time is True


def test_no_graph_rows_are_fetched_for_an_explicit_graph() -> None:
    assert _specification().fetch_graph_rows(None) == []  # type: ignore[arg-type]
