#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._metric_expression import (
    Metric,
    MetricExpression,
)
from cmk.gui.graphing._metric_operation import LineType, MetricOpOperator, MetricOpRRDSource
from cmk.gui.graphing._translated_metrics import (
    Original,
    TranslatedMetric,
)
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


@pytest.mark.parametrize(
    ("orig_names", "scales", "expected_operation"),
    [
        pytest.param(
            ["metric-name"],
            [1.0],
            MetricOpRRDSource(
                site_id=SiteId("Site-ID"),
                host_name=HostName("HostName"),
                service_name="Service description",
                metric_name="metric-name",
                consolidation_func_name=None,
                scale=1.0,
            ),
            id="no translation",
        ),
        pytest.param(
            ["metric-name", "old-metric-name"],
            [1.0, 2.0],
            MetricOpOperator(
                operator_name="MERGE",
                operands=[
                    MetricOpRRDSource(
                        site_id=SiteId("Site-ID"),
                        host_name=HostName("HostName"),
                        service_name="Service description",
                        metric_name="metric-name",
                        consolidation_func_name=None,
                        scale=1.0,
                    ),
                    MetricOpRRDSource(
                        site_id=SiteId("Site-ID"),
                        host_name=HostName("HostName"),
                        service_name="Service description",
                        metric_name="old-metric-name",
                        consolidation_func_name=None,
                        scale=2.0,
                    ),
                ],
            ),
            id="translation",
        ),
    ],
)
def test_metric_to_metric_operation(
    orig_names: Sequence[str],
    scales: Sequence[int | float],
    expected_operation: MetricOpOperator | MetricOpRRDSource,
) -> None:
    assert (
        Metric("metric-name").to_metric_operation(
            SiteId("Site-ID"),
            HostName("HostName"),
            "Service description",
            {
                "metric-name": TranslatedMetric(
                    originals=[Original(n, s) for n, s in zip(orig_names, scales)],
                    value=23.5,
                    scalar={},
                    auto_graph=False,
                    title="Title",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
            },
            None,
        )
        == expected_operation
    )
