#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.graphing._graph_specification import (
    compute_warn_crit_rules_from_translated_metric,
    HorizontalRule,
)
from cmk.gui.graphing._translated_metrics import (
    Original,
    ScalarBounds,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    user_specific_unit,
)
from cmk.gui.unit_formatter import AutoPrecision
from cmk.gui.utils.temperate_unit import TemperatureUnit


@pytest.mark.parametrize(
    "translated_metric, horizontal_rules",
    [
        pytest.param(
            TranslatedMetric(
                originals=[Original("metric", 7.0)],
                value=7.0,
                scalar=ScalarBounds(),
                auto_graph=True,
                title="Metric",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            [],
            id="no-scalars",
        ),
        pytest.param(
            TranslatedMetric(
                originals=[Original("metric", 7.0)],
                value=7.0,
                scalar=ScalarBounds(warn=5.0, crit=10.0),
                auto_graph=True,
                title="Metric",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            [
                HorizontalRule(value=5.0, rendered_value="5", color="#ffd000", title="Warning"),
                HorizontalRule(value=10.0, rendered_value="10", color="#ff3232", title="Critical"),
            ],
            id="scalars-pos",
        ),
        pytest.param(
            TranslatedMetric(
                originals=[Original("metric", -7.0)],
                value=-7.0,
                scalar=ScalarBounds(warn=-5.0, crit=-10.0),
                auto_graph=True,
                title="Metric",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            [
                HorizontalRule(value=-5.0, rendered_value="-5", color="#ffd000", title="Warning"),
                HorizontalRule(
                    value=-10.0, rendered_value="-10", color="#ff3232", title="Critical"
                ),
            ],
            id="scalars-neg",
        ),
        pytest.param(
            TranslatedMetric(
                originals=[Original("metric", 7.0)],
                value=7.0,
                scalar=ScalarBounds(warn=5.0, crit=float("inf")),
                auto_graph=True,
                title="Metric",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            [HorizontalRule(value=5.0, rendered_value="5", color="#ffd000", title="Warning")],
            id="scalars-crit-pos-inf",
        ),
        pytest.param(
            TranslatedMetric(
                originals=[Original("metric", -7.0)],
                value=-7.0,
                scalar=ScalarBounds(warn=-5.0, crit=float("-inf")),
                auto_graph=True,
                title="Metric",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            [HorizontalRule(value=-5.0, rendered_value="-5", color="#ffd000", title="Warning")],
            id="scalars-crit-neg-inf",
        ),
        pytest.param(
            TranslatedMetric(
                originals=[Original("metric", 7.0)],
                value=7.0,
                scalar=ScalarBounds(warn=float("inf"), crit=float("inf")),
                auto_graph=True,
                title="Metric",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            [],
            id="scalars-pos-inf",
        ),
        pytest.param(
            TranslatedMetric(
                originals=[Original("metric", -7.0)],
                value=-7.0,
                scalar=ScalarBounds(warn=float("-inf"), crit=float("-inf")),
                auto_graph=True,
                title="Metric",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#111111",
            ),
            [],
            id="scalars-neg-inf",
        ),
    ],
)
def test_compute_warn_crit_rules_from_translated_metric(
    translated_metric: TranslatedMetric, horizontal_rules: Sequence[HorizontalRule]
) -> None:
    assert (
        compute_warn_crit_rules_from_translated_metric(
            user_specific_unit(translated_metric.unit_spec, TemperatureUnit.CELSIUS),
            translated_metric,
        )
        == horizontal_rules
    )
