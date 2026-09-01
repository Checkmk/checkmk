#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title as TitleV1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.gui.graphing._evaluations_from_api import (
    evaluate_graph_plugin_metrics,
    evaluate_graph_plugin_range,
    evaluate_graph_plugin_scalars,
    evaluate_graph_plugin_title,
    evaluate_quantity,
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

UNIT = metrics_v1.Unit(metrics_v1.DecimalNotation(""))


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
                    scalar=ScalarBounds(max_=10),
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
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                compound_lines=["metric"],
            ),
            None,
            id="graph-no-range",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                minimal_range=graphs_v1.MinimalRange(1, 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=200.0),
            id="graph-with-range-numbers",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                minimal_range=graphs_v1.MinimalRange(1, "metric"),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=123.456),
            id="graph-with-range-upper-known-metric",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                minimal_range=graphs_v1.MinimalRange(1, "unknown_metric"),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=None),
            id="graph-with-range-upper-metric",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                minimal_range=graphs_v1.MinimalRange("metric", 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=123.456, max=200),
            id="graph-with-range-lower-known-metric",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                minimal_range=graphs_v1.MinimalRange("unknown_metric", 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=None, max=200),
            id="graph-with-range-lower-metric",
        ),
        pytest.param(
            graphs_v1.Bidirectional(
                name="graph",
                title=TitleV1("Graph"),
                upper=graphs_v1.Graph(
                    name="graph_upper",
                    title=TitleV1("Graph upper"),
                    minimal_range=graphs_v1.MinimalRange("metric", 200),
                    compound_lines=["metric"],
                ),
                lower=graphs_v1.Graph(
                    name="graph_lower",
                    title=TitleV1("Graph lower"),
                    minimal_range=graphs_v1.MinimalRange(0, "metric"),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=200),
            id="bidirectional",
        ),
        pytest.param(
            graphs_v1.Bidirectional(
                name="graph",
                title=TitleV1("Graph"),
                upper=graphs_v1.Graph(
                    name="graph_upper",
                    title=TitleV1("Graph upper"),
                    minimal_range=graphs_v1.MinimalRange("metric1", 300),
                    compound_lines=["metric"],
                ),
                lower=graphs_v1.Graph(
                    name="graph_lower",
                    title=TitleV1("Graph lower"),
                    minimal_range=graphs_v1.MinimalRange(0, 200),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=300),
            id="bidirectional-no-upper-min",
        ),
        pytest.param(
            graphs_v1.Bidirectional(
                name="graph",
                title=TitleV1("Graph"),
                upper=graphs_v1.Graph(
                    name="graph_upper",
                    title=TitleV1("Graph upper"),
                    minimal_range=graphs_v1.MinimalRange(0, "metric1"),
                    compound_lines=["metric"],
                ),
                lower=graphs_v1.Graph(
                    name="graph_lower",
                    title=TitleV1("Graph lower"),
                    minimal_range=graphs_v1.MinimalRange(100, 300),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=300),
            id="bidirectional-no-upper-max",
        ),
    ],
)
def test_evaluate_graph_plugin_range(
    graph_plugin: graphs_v1.Graph | graphs_v1.Bidirectional, expected: MinimalVerticalRange | None
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
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                compound_lines=["metric"],
            ),
            [],
            id="graph-no-scalars",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                compound_lines=["metric"],
                simple_lines=[
                    metrics_v1.WarningOf("metric1"),
                    metrics_v1.CriticalOf("metric1"),
                ],
            ),
            [],
            id="graph-with-scalars-no-values",
        ),
        pytest.param(
            graphs_v1.Graph(
                name="graph",
                title=TitleV1("Graph"),
                compound_lines=["metric"],
                simple_lines=[
                    metrics_v1.WarningOf("metric"),
                    metrics_v1.CriticalOf("metric"),
                ],
            ),
            [
                HorizontalRule(
                    value=56.78,
                    rendered_value="56.78 U",
                    color="#ff3232",
                    title="Critical of metric",
                ),
                HorizontalRule(
                    value=12.34,
                    rendered_value="12.34 U",
                    color="#ffd000",
                    title="Warning of metric",
                ),
            ],
            id="graph-with-scalars-with-values",
        ),
        pytest.param(
            graphs_v1.Bidirectional(
                name="graph",
                title=TitleV1("Graph"),
                upper=graphs_v1.Graph(
                    name="graph_upper",
                    title=TitleV1("Graph upper"),
                    minimal_range=graphs_v1.MinimalRange("metric", 200),
                    compound_lines=["metric"],
                    simple_lines=[
                        metrics_v1.WarningOf("metric"),
                    ],
                ),
                lower=graphs_v1.Graph(
                    name="graph_lower",
                    title=TitleV1("Graph lower"),
                    minimal_range=graphs_v1.MinimalRange(0, "metric"),
                    compound_lines=["metric"],
                    simple_lines=[
                        metrics_v1.CriticalOf("metric"),
                    ],
                ),
            ),
            [
                HorizontalRule(
                    value=12.34,
                    rendered_value="12.34 U",
                    color="#ffd000",
                    title="Warning of metric",
                ),
                HorizontalRule(
                    value=-56.78,
                    rendered_value="56.78 U",
                    color="#ff3232",
                    title="Critical of metric",
                ),
            ],
            id="bidirectional",
        ),
    ],
)
def test_evaluate_graph_plugin_scalars(
    graph_plugin: graphs_v1.Graph | graphs_v1.Bidirectional, expected: Sequence[HorizontalRule]
) -> None:
    assert (
        evaluate_graph_plugin_scalars(
            {},
            graph_plugin,
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
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        == expected
    )


def test_evaluate_graph_plugin_scalars_bidirectional_drops_out_of_range_rules() -> None:
    # warn_lower is negative: in the upper sub-graph it would render below
    # zero, in the lower sub-graph (factor=-1) it would render above zero —
    # outside either half of the bidirectional visualization. The rule must
    # be dropped.
    rules = evaluate_graph_plugin_scalars(
        {},
        graphs_v2_unstable.Bidirectional(
            name="graph",
            title=TitleV1("Graph"),
            upper=graphs_v2_unstable.Graph(
                name="graph_upper",
                title=TitleV1("Graph upper"),
                compound_lines=["metric"],
                simple_lines=[metrics_v2_unstable.LowerWarningOf("metric")],
            ),
            lower=graphs_v2_unstable.Graph(
                name="graph_lower",
                title=TitleV1("Graph lower"),
                compound_lines=["metric"],
                simple_lines=[metrics_v2_unstable.LowerWarningOf("metric")],
            ),
        ),
        {
            "metric": TranslatedMetric(
                originals=[Original("metric", 1.0)],
                value=123.456,
                scalar=ScalarBounds(warn_lower=-2.0),
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
    assert rules == []


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
    result = evaluate_quantity({}, quantity, translated_metrics)
    assert result.is_ok()
    assert result.ok.value == expected_value
