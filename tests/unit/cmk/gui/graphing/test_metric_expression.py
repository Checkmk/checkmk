#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._metric_expression import (
    Metric,
    MetricExpression,
)
from cmk.gui.graphing._metric_operation import LineType
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation


@pytest.mark.parametrize(
    "line_type, expected_line_type",
    [
        pytest.param("line", "-line", id="'line'->'-line'"),
        pytest.param("-line", "line", id="'-line'->'line'"),
        pytest.param("area", "-area", id="'area'->'-area'"),
        pytest.param("-area", "area", id="'-area'->'area'"),
        pytest.param("stack", "-stack", id="'stack'->'-stack'"),
        pytest.param("-stack", "stack", id="'-stack'->'stack'"),
    ],
)
def test_metric_expression_mirror(line_type: LineType, expected_line_type: LineType) -> None:
    assert MetricExpression(
        Metric("metric-name"),
        unit_spec=ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol=""),
            precision=AutoPrecision(digits=2),
        ),
        color="#000000",
        line_type=line_type,
        title="Title",
    ).mirror() == MetricExpression(
        Metric("metric-name"),
        unit_spec=ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol=""),
            precision=AutoPrecision(digits=2),
        ),
        color="#000000",
        line_type=expected_line_type,
        title="Title",
    )
