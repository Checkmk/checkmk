#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title as TitleV1
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.gui.graphing._evaluations_from_api import (
    _evaluate_quantity,
    evaluate_graph_plugin_metrics,
    GraphedMetrics,
)
from cmk.gui.graphing._graph_metric_expressions import GraphMetricRRDSource
from cmk.gui.graphing._graph_specification import (
    GraphMetric,
)
from cmk.gui.graphing._translated_metrics import (
    Original,
    ScalarBounds,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.unit_formatter import AutoPrecision
from cmk.utils.servicename import ServiceName

UNIT = metrics_v1.Unit(metrics_v1.DecimalNotation(""))


@pytest.mark.parametrize(
    "graph_plugin, translated_metrics, expected",
    [
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                compound_lines=["metric1"],
            ),
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(warn=12.34, crit=56.78),
                    auto_graph=True,
                    title="Metric",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                )
            },
            GraphedMetrics(graph_metrics=[], metric_names=[]),
            id="graph-no-graphed-metrics",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                compound_lines=["metric"],
            ),
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(warn=12.34, crit=56.78),
                    auto_graph=True,
                    title="Metric",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                )
            },
            GraphedMetrics(
                graph_metrics=[
                    GraphMetric(
                        title="metric",
                        line_type="stack",
                        operation=GraphMetricRRDSource(
                            site_id=SiteId("site-id"),
                            host_name=HostName("host-name"),
                            service_name=ServiceName("service-name"),
                            metric_name="metric",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        unit=ConvertibleUnitSpecification(
                            notation=DecimalNotation(symbol="U"),
                            precision=AutoPrecision(digits=2),
                        ),
                        color="#123456",
                    ),
                ],
                metric_names=["metric"],
            ),
            id="graph-with-graphed-metrics-no-predictive",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                compound_lines=["metric"],
            ),
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(warn=12.34, crit=56.78),
                    auto_graph=True,
                    title="Metric",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "predict_metric": TranslatedMetric(
                    originals=[Original("predict_metric", 1.0)],
                    value=56.78,
                    auto_graph=True,
                    scalar=ScalarBounds(),
                    title="Prediction of Metric (upper levels)",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "predict_lower_metric": TranslatedMetric(
                    originals=[Original("predict_lower_metric", 1.0)],
                    value=12.34,
                    auto_graph=True,
                    scalar=ScalarBounds(),
                    title="Prediction of Metric (lower levels)",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            GraphedMetrics(
                graph_metrics=[
                    GraphMetric(
                        title="metric",
                        line_type="stack",
                        operation=GraphMetricRRDSource(
                            site_id=SiteId("site-id"),
                            host_name=HostName("host-name"),
                            service_name=ServiceName("service-name"),
                            metric_name="metric",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        unit=ConvertibleUnitSpecification(
                            notation=DecimalNotation(symbol="U"),
                            precision=AutoPrecision(digits=2),
                        ),
                        color="#123456",
                    ),
                    GraphMetric(
                        title="Prediction of metric (upper levels)",
                        line_type="line",
                        operation=GraphMetricRRDSource(
                            site_id=SiteId("site-id"),
                            host_name=HostName("host-name"),
                            service_name=ServiceName("service-name"),
                            metric_name="predict_metric",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        unit=ConvertibleUnitSpecification(
                            notation=DecimalNotation(symbol="U"),
                            precision=AutoPrecision(digits=2),
                        ),
                        color="#123456",
                    ),
                    GraphMetric(
                        title="Prediction of metric (lower levels)",
                        line_type="line",
                        operation=GraphMetricRRDSource(
                            site_id=SiteId("site-id"),
                            host_name=HostName("host-name"),
                            service_name=ServiceName("service-name"),
                            metric_name="predict_lower_metric",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        unit=ConvertibleUnitSpecification(
                            notation=DecimalNotation(symbol="U"),
                            precision=AutoPrecision(digits=2),
                        ),
                        color="#123456",
                    ),
                ],
                metric_names=["metric", "predict_lower_metric", "predict_metric"],
            ),
            id="graph-with-graphed-metrics-with-predictive",
        ),
        pytest.param(
            graphs_v1.Bidirectional(
                name="graph",
                title=TitleV1("Graph"),
                upper=graphs_v1.Graph(
                    name="graph_upper",
                    title=TitleV1("Graph upper"),
                    compound_lines=["metric_upper"],
                ),
                lower=graphs_v1.Graph(
                    name="graph_lower",
                    title=TitleV1("Graph lower"),
                    compound_lines=["metric_lower"],
                ),
            ),
            {
                "metric_upper": TranslatedMetric(
                    originals=[Original("metric_upper", 1.0)],
                    value=12.45,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric upper",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#111111",
                ),
                "metric_lower": TranslatedMetric(
                    originals=[Original("metric_lower", 1.0)],
                    value=12.45,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric lower",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#222222",
                ),
            },
            GraphedMetrics(
                graph_metrics=[
                    GraphMetric(
                        title="metric_upper",
                        line_type="stack",
                        operation=GraphMetricRRDSource(
                            site_id=SiteId("site-id"),
                            host_name=HostName("host-name"),
                            service_name=ServiceName("service-name"),
                            metric_name="metric_upper",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        unit=ConvertibleUnitSpecification(
                            notation=DecimalNotation(symbol="U"),
                            precision=AutoPrecision(digits=2),
                        ),
                        color="#111111",
                    ),
                    GraphMetric(
                        title="metric_lower",
                        line_type="-stack",
                        operation=GraphMetricRRDSource(
                            site_id=SiteId("site-id"),
                            host_name=HostName("host-name"),
                            service_name=ServiceName("service-name"),
                            metric_name="metric_lower",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        unit=ConvertibleUnitSpecification(
                            notation=DecimalNotation(symbol="U"),
                            precision=AutoPrecision(digits=2),
                        ),
                        color="#222222",
                    ),
                ],
                metric_names=["metric_lower", "metric_upper"],
            ),
            id="bidrectional-with-graphed-metrics",
        ),
    ],
)
def test_evaluate_graph_plugin_metrics(
    graph_plugin: graphs_v1.Graph | graphs_v1.Bidirectional,
    translated_metrics: Mapping[str, TranslatedMetric],
    expected: GraphedMetrics,
) -> None:
    assert (
        evaluate_graph_plugin_metrics(
            {},
            SiteId("site-id"),
            HostName("host-name"),
            ServiceName("service-name"),
            "max",
            graph_plugin,
            translated_metrics,
        )
        == expected
    )


def _make_translated_metric(name: str, scalar: ScalarBounds) -> TranslatedMetric:
    return TranslatedMetric(
        originals=[Original(name, 1.0)],
        value=10.0,
        scalar=scalar,
        auto_graph=False,
        title="Title 1",
        unit_spec=ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol=""),
            precision=AutoPrecision(digits=2),
        ),
        color="#123456",
    )


@pytest.mark.parametrize(
    "quantity, translated_metrics, expected_value",
    [
        pytest.param(
            "name",
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            10.0,
            id="metric-name",
        ),
        pytest.param(
            metrics_v1.Constant(
                TitleV1("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
                5.0,
            ),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_v1.Constant",
        ),
        pytest.param(
            metrics_v1.WarningOf("name"),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(warn=5.0),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_v1.WarningOf",
        ),
        pytest.param(
            metrics_v1.CriticalOf("name"),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(crit=5.0),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_v1.CriticalOf",
        ),
        pytest.param(
            metrics_v1.MinimumOf("name", metrics_v1.Color.BLUE),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(min_=5.0),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_v1.MinimumOf",
        ),
        pytest.param(
            metrics_v1.MaximumOf("name", metrics_v1.Color.BLUE),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(max_=5.0),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_v1.MaximumOf",
        ),
        pytest.param(
            metrics_v1.Sum(
                TitleV1("Title"),
                metrics_v1.Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=5.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            15.0,
            id="metrics_v1.Sum",
        ),
        pytest.param(
            metrics_v1.Product(
                TitleV1("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=5.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            50.0,
            id="metrics_v1.Product",
        ),
        pytest.param(
            metrics_v1.Difference(
                TitleV1("Title"),
                metrics_v1.Color.BLUE,
                minuend="name1",
                subtrahend="name2",
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=3.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            7.0,
            id="metrics_v1.Difference",
        ),
        pytest.param(
            metrics_v1.Fraction(
                TitleV1("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
                dividend="name1",
                divisor="name2",
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=5.0,
                    scalar=ScalarBounds(),
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            2.0,
            id="metrics_v1.Fraction",
        ),
        pytest.param(
            metrics_v2_unstable.LowerWarningOf("name"),
            {
                "name": _make_translated_metric("name", ScalarBounds(warn=99.0, warn_lower=3.0)),
            },
            3.0,
            id="metrics_v2_unstable.LowerWarningOf",
        ),
        pytest.param(
            metrics_v2_unstable.LowerCriticalOf("name"),
            {
                "name": _make_translated_metric("name", ScalarBounds(crit=99.0, crit_lower=2.0)),
            },
            2.0,
            id="metrics_v2_unstable.LowerCriticalOf",
        ),
    ],
)
def test_evaluate_quantity(
    quantity: (
        str
        | metrics_v1.Constant
        | metrics_v1.WarningOf
        | metrics_v1.CriticalOf
        | metrics_v1.MinimumOf
        | metrics_v1.MaximumOf
        | metrics_v1.Sum
        | metrics_v1.Product
        | metrics_v1.Difference
        | metrics_v1.Fraction
        | metrics_v2_unstable.LowerWarningOf
        | metrics_v2_unstable.LowerCriticalOf
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
    expected_value: float,
) -> None:
    result = _evaluate_quantity({}, quantity, translated_metrics)
    assert result.is_ok()
    assert result.ok.value == expected_value
