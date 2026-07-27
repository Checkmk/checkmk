#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    Metric,
    MetricName,
    PerformanceData,
    RRDMetric,
    ScalarKind,
    ScalarOf,
    Service,
    ServiceName,
    TimeRange,
    TimeSeries,
)
from cmk.gui.graphing._engine_dispatch import CommonGraphOptions
from cmk.gui.graphing._engine_rrd import RawPerformanceValue
from cmk.gui.graphing._engine_template_graphs import (
    build_template_graphs,
    evaluate_template_graphs,
)
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification

_SERVICE = Service(host_name=HostName("h"), service_name=ServiceName("svc"))
_SPEC = TemplateGraphSpecification(site=None, host_name=HostAddress("h"), service_description="svc")
_METRIC = "x"
_DISCOVERY_RANGE = TimeRange(start=0, end=60, step=10)


@dataclass
class _FakeRRDFetchMetricNames:
    metric_names: Sequence[str] = (_METRIC,)

    def __call__(self) -> Mapping[Service, frozenset[MetricName]]:
        return {_SERVICE: frozenset(MetricName(name) for name in self.metric_names)}


@dataclass
class _FakeRRDFetchData:
    values: Mapping[str, RawPerformanceValue] = field(
        default_factory=lambda: {_METRIC: RawPerformanceValue(value=1.0)}
    )
    requested_ranges: list[TimeRange] = field(default_factory=list)

    def __call__(
        self,
        metrics: Sequence[Metric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[Metric, Sequence[FetchedData]]:
        self.requested_ranges.append(time_range)
        result: dict[Metric, Sequence[FetchedData]] = {}
        for metric in metrics:
            if not isinstance(metric, RRDMetric):
                continue
            raw = self.values.get(str(metric.metric_name))
            performance_data = None if raw is None else PerformanceData(value=raw.value)
            result[metric] = [
                FetchedData(
                    performance_data=performance_data,
                    time_series=TimeSeries(time_range=time_range, values=[1.0, 1.0, 1.0]),
                )
            ]
        return result


def test_template_lifecycle_discover_and_update() -> None:
    # Discovery builds the display-resolved graphs (every curve carries its attributes, but no data and no
    # render parameters); the per-type update evaluates them over freshly fetched data for the range it is
    # given. The unclaimed metric becomes a fallback single-metric graph that carries the four threshold
    # rules the engine builds itself.
    fetch_data = _FakeRRDFetchData()
    graphs = [
        built.graph
        for built in build_template_graphs(
            _SPEC,
            registered_graphs=[],
            registered_metrics={},
            fetch_metric_names=_FakeRRDFetchMetricNames(),
        )
    ]
    [fallback] = [graph for graph in graphs if graph.name == _METRIC]
    assert [
        rule.curve.quantity.scalar_kind
        for rule in fallback.rules
        if isinstance(rule.curve.quantity, ScalarOf)
    ] == [
        ScalarKind.WARNING,
        ScalarKind.CRITICAL,
        ScalarKind.LOWER_WARNING,
        ScalarKind.LOWER_CRITICAL,
    ]
    # Discovery fetches performance data only, never the time series.
    assert fetch_data.requested_ranges == []

    evaluated = evaluate_template_graphs(
        graphs=graphs,
        options=CommonGraphOptions(
            consolidation_function=ConsolidationFunction.MAX,
            time_range=_DISCOVERY_RANGE,
        ),
        fetch_data=fetch_data,
    )

    assert len(evaluated) == len(graphs)
    # The update fetches the series for the range it is given.
    assert fetch_data.requested_ranges
    assert all(time_range == _DISCOVERY_RANGE for time_range in fetch_data.requested_ranges)


def test_template_graphs_filter_by_graph_id() -> None:
    def _build(graph_id: str | None) -> Sequence[str]:
        return [
            built.graph.name
            for built in build_template_graphs(
                TemplateGraphSpecification(
                    site=None,
                    host_name=HostAddress("h"),
                    service_description="svc",
                    graph_id=graph_id,
                ),
                registered_graphs=[],
                registered_metrics={},
                fetch_metric_names=_FakeRRDFetchMetricNames(),
            )
        ]

    assert _build(_METRIC) == [_METRIC]
    assert _build("does_not_exist") == []


def test_template_lifecycle_rejects_mixed_units() -> None:
    # A template graph has a single value axis, so a plugin drawing curves of different units cannot
    # share it — discovery rejects it (legacy parity).
    with pytest.raises(MKGeneralException, match="different units"):
        build_template_graphs(
            _SPEC,
            registered_graphs=[
                graphs_v1.Graph(
                    name="mixed",
                    title=Title("Mixed"),
                    simple_lines=["bytes_metric", "seconds_metric"],
                )
            ],
            registered_metrics={
                "bytes_metric": metrics_v1.Metric(
                    name="bytes_metric",
                    title=Title("Bytes"),
                    unit=metrics_v1.Unit(metrics_v1.DecimalNotation("B")),
                    color=metrics_v1.Color.BLUE,
                ),
                "seconds_metric": metrics_v1.Metric(
                    name="seconds_metric",
                    title=Title("Seconds"),
                    unit=metrics_v1.Unit(metrics_v1.DecimalNotation("s")),
                    color=metrics_v1.Color.GREEN,
                ),
            },
            fetch_metric_names=_FakeRRDFetchMetricNames(("bytes_metric", "seconds_metric")),
        )
