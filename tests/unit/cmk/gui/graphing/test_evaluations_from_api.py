#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing import v1 as graphing_api
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.graphing._evaluations_from_api import (
    evaluate_graph_plugin_metrics,
    evaluate_graph_plugin_range,
    evaluate_graph_plugin_scalars,
    evaluate_graph_plugin_title,
    GraphedMetrics,
)
from cmk.gui.graphing._graph_metric_expressions import GraphMetricRRDSource
from cmk.gui.graphing._graph_specification import (
    GraphMetric,
    HorizontalRule,
    MinimalVerticalRange,
)
from cmk.gui.graphing._translated_metrics import (
    Original,
    ScalarBounds,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.unit_formatter import AutoPrecision
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.servicename import ServiceName


@pytest.mark.parametrize(
    "graph_plugin_title, expected",
    [
        pytest.param(
            "Graph",
            "Graph",
            id="graph-no-expression",
        ),
        pytest.param(
            'Graph - _EXPRESSION:{"metric":"metric1","scalar":"max"} Items',
            "Graph",
            id="graph-with-expression-no-values",
        ),
        pytest.param(
            'Graph - _EXPRESSION:{"metric":"metric","scalar":"max"} Items',
            "Graph - 10 Items",
            id="graph-with-expression-with-values",
        ),
    ],
)
def test_evaluate_graph_plugin_title(graph_plugin_title: str, expected: str) -> None:
    assert (
        evaluate_graph_plugin_title(
            {},
            graph_plugin_title,
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(max=10),
                    auto_graph=True,
                    title="Metric",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                )
            },
        )
        == expected
    )


@pytest.mark.parametrize(
    "graph_plugin, expected",
    [
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric"],
            ),
            None,
            id="graph-no-range",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange(1, 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=200.0),
            id="graph-with-range-numbers",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange(1, "metric"),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=123.456),
            id="graph-with-range-upper-known-metric",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange(1, "unknown_metric"),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=None),
            id="graph-with-range-upper-metric",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange("metric", 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=123.456, max=200),
            id="graph-with-range-lower-known-metric",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange("unknown_metric", 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=None, max=200),
            id="graph-with-range-lower-metric",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    minimal_range=graphs_api.MinimalRange("metric", 200),
                    compound_lines=["metric"],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
                    minimal_range=graphs_api.MinimalRange(0, "metric"),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=200),
            id="bidirectional",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    minimal_range=graphs_api.MinimalRange("metric1", 300),
                    compound_lines=["metric"],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
                    minimal_range=graphs_api.MinimalRange(0, 200),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=300),
            id="bidirectional-no-upper-min",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    minimal_range=graphs_api.MinimalRange(0, "metric1"),
                    compound_lines=["metric"],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
                    minimal_range=graphs_api.MinimalRange(100, 300),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=300),
            id="bidirectional-no-upper-max",
        ),
    ],
)
def test_evaluate_graph_plugin_range(
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional, expected: MinimalVerticalRange | None
) -> None:
    assert (
        evaluate_graph_plugin_range(
            {},
            graph_plugin,
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                )
            },
        )
        == expected
    )


@pytest.mark.parametrize(
    "graph_plugin, expected",
    [
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric"],
            ),
            [],
            id="graph-no-scalars",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric"],
                simple_lines=[
                    metrics_api.WarningOf("metric1"),
                    metrics_api.CriticalOf("metric1"),
                ],
            ),
            [],
            id="graph-with-scalars-no-values",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric"],
                simple_lines=[
                    metrics_api.WarningOf("metric"),
                    metrics_api.CriticalOf("metric"),
                ],
            ),
            [
                HorizontalRule(
                    value=12.34,
                    rendered_value="12.34 U",
                    color="#ffd000",
                    title="Warning of Metric",
                ),
                HorizontalRule(
                    value=56.78,
                    rendered_value="56.78 U",
                    color="#ff3232",
                    title="Critical of Metric",
                ),
            ],
            id="graph-with-scalars-with-values",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    minimal_range=graphs_api.MinimalRange("metric", 200),
                    compound_lines=["metric"],
                    simple_lines=[
                        metrics_api.WarningOf("metric"),
                    ],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
                    minimal_range=graphs_api.MinimalRange(0, "metric"),
                    compound_lines=["metric"],
                    simple_lines=[
                        metrics_api.CriticalOf("metric"),
                    ],
                ),
            ),
            [
                HorizontalRule(
                    value=12.34,
                    rendered_value="12.34 U",
                    color="#ffd000",
                    title="Warning of Metric",
                ),
                HorizontalRule(
                    value=-56.78,
                    rendered_value="56.78 U",
                    color="#ff3232",
                    title="Critical of Metric",
                ),
            ],
            id="bidirectional",
        ),
    ],
)
def test_evaluate_graph_plugin_scalars(
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional, expected: Sequence[HorizontalRule]
) -> None:
    assert (
        evaluate_graph_plugin_scalars(
            {},
            graph_plugin,
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(
                        warn=12.34,
                        crit=56.78,
                    ),
                    auto_graph=True,
                    title="Metric",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                )
            },
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        == expected
    )


@pytest.mark.parametrize(
    "graph_plugin, translated_metrics, expected",
    [
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric1"],
            ),
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(
                        warn=12.34,
                        crit=56.78,
                    ),
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
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric"],
            ),
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(
                        warn=12.34,
                        crit=56.78,
                    ),
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
                        title="Metric",
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
                    )
                ],
                metric_names=["metric"],
            ),
            id="graph-with-graphed-metrics-no-predictive",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric"],
            ),
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(
                        warn=12.34,
                        crit=56.78,
                    ),
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
                        title="Metric",
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
                        title="Prediction of Metric (upper levels)",
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
                        title="Prediction of Metric (lower levels)",
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
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    compound_lines=["metric_upper"],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
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
                        title="Metric_Upper",
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
                        title="Metric_Lower",
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
                metric_names=["metric_upper", "metric_lower"],
            ),
            id="bidrectional-with-graphed-metrics",
        ),
    ],
)
def test_evaluate_graph_plugin_metrics(
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional,
    translated_metrics: Mapping[str, TranslatedMetric],
    expected: GraphedMetrics,
) -> None:
    assert (
        evaluate_graph_plugin_metrics(
            {},
            SiteId("site-id"),
            HostName("host-name"),
            ServiceName("service-name"),
            graph_plugin,
            translated_metrics,
        )
        == expected
    )
