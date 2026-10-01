#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.graphing_engine import MetricName, PerformanceData
from cmk.gui.dashboard.dashlet.dashlets.status_helpers import purge_evaluated_metric_for_js
from cmk.gui.graphing import EvaluatedMetric
from cmk.gui.unit_formatter import (
    AutoPrecision,
    DecimalFormatter,
    IECFormatter,
    NotationFormatter,
    StrictPrecision,
)
from cmk.shared_typing.cmk_time_series_graph import Precision, UnitFormat


def _metric(formatter: NotationFormatter, performance_data: PerformanceData) -> EvaluatedMetric:
    return EvaluatedMetric(
        name=MetricName("load1"),
        title="Load",
        color="#000000",
        formatter=formatter,
        unit_format=UnitFormat(
            notation="decimal", symbol="", precision=Precision(type="auto", digits=2)
        ),
        performance_data=performance_data,
    )


@pytest.mark.parametrize(
    ["formatter", "expected_unit"],
    [
        pytest.param(
            DecimalFormatter(symbol="Hz", precision=AutoPrecision(digits=3)),
            {
                "formatter_type": "DecimalFormatter",
                "symbol": "Hz",
                "precision_type": "auto",
                "precision_digits": 3,
                "stepping": None,
            },
            id="standard stepping",
        ),
        pytest.param(
            IECFormatter(symbol="X", precision=StrictPrecision(digits=2)),
            {
                "formatter_type": "IECFormatter",
                "symbol": "X",
                "precision_type": "strict",
                "precision_digits": 2,
                "stepping": "binary",
            },
            id="binary stepping",
        ),
    ],
)
def test_the_unit_describes_the_formatter_of_the_metric(
    formatter: NotationFormatter, expected_unit: Mapping[str, object]
) -> None:
    purged = purge_evaluated_metric_for_js(_metric(formatter, PerformanceData(value=1.0)))

    assert purged["unit"] == expected_unit


def test_the_bounds_hold_only_the_levels_the_metric_reports() -> None:
    metric = _metric(
        DecimalFormatter(symbol="", precision=AutoPrecision(digits=2)),
        PerformanceData(value=1.0, warning=2.0, maximum=4.0),
    )

    assert purge_evaluated_metric_for_js(metric)["bounds"] == {"warn": 2.0, "max": 4.0}
