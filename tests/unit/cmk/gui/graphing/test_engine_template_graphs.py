#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    MetricName,
    MetricProtocol,
    PerformanceData,
    RRDMetric,
    ScalarKind,
    ScalarOf,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
    TimeSeries,
)
from cmk.gui.graphing._engine_dispatch import CommonGraphOptions
from cmk.gui.graphing._engine_perfdata import RawPerformanceValue
from cmk.gui.graphing._engine_source import FetchDiagnostics
from cmk.gui.graphing._engine_template_graphs import (
    _EvaluateTemplateGraphs,
    build_template_graphs,
)
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification

_SERVICE = Service(
    host_name=HostName("h"), service_name=ServiceName("svc"), site_id=SiteID("mysite")
)
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
    diagnostics: FetchDiagnostics = field(default_factory=FetchDiagnostics)

    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
        self.requested_ranges.append(time_range)
        result: dict[MetricProtocol, Sequence[FetchedData]] = {}
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

    evaluate = _EvaluateTemplateGraphs(
        CommonGraphOptions(
            consolidation_function=ConsolidationFunction.MAX,
            time_range=_DISCOVERY_RANGE,
        ),
        fetch_data,
    )
    evaluated = [one for graph in graphs for one in evaluate(graph).graphs]

    assert len(evaluated) == len(graphs)
    # The update fetches the series for the range it is given.
    assert fetch_data.requested_ranges
    assert all(time_range == _DISCOVERY_RANGE for time_range in fetch_data.requested_ranges)


def test_template_build_carries_a_per_graph_add_to_specification() -> None:
    # A built graph carries a copy of the seed specification addressed to that graph by id, so the
    # add-to endpoints can replay it; the host, service and site are kept from the seed.
    [built] = build_template_graphs(
        _SPEC,
        registered_graphs=[],
        registered_metrics={},
        fetch_metric_names=_FakeRRDFetchMetricNames(),
    )
    assert built.graph.name == _METRIC
    assert isinstance(built.specification, TemplateGraphSpecification)
    # This is a fallback single-metric graph, named after the bare metric by the engine but
    # resolvable by legacy only as "METRIC_<name>", so that is how the spec must address it.
    assert built.specification.graph_id == f"METRIC_{_METRIC}"
    # The id round-trips: replaying the spec yields exactly the graph it was built for.
    assert [
        replayed.graph.name
        for replayed in build_template_graphs(
            built.specification,
            registered_graphs=[],
            registered_metrics={},
            fetch_metric_names=_FakeRRDFetchMetricNames(),
        )
    ] == [_METRIC]
    assert built.specification.host_name == _SPEC.host_name
    assert built.specification.service_description == _SPEC.service_description
    # The seed carried no site; the metric-name fetch resolved it, so the spec is complete.
    assert built.specification.site == SiteId("mysite")


def test_template_build_addresses_plugin_graphs_by_the_plugin_name() -> None:
    # A graph backed by a registered plug-in is stored under the plug-in's own name, unprefixed.
    registered_graphs = [
        graphs_v1.Graph(name="plugin_graph", title=Title("Plugin"), simple_lines=[_METRIC])
    ]
    registered_metrics = {
        _METRIC: metrics_v1.Metric(
            name=_METRIC,
            title=Title("X"),
            unit=metrics_v1.Unit(metrics_v1.DecimalNotation("B")),
            color=metrics_v1.Color.BLUE,
        )
    }
    [built] = build_template_graphs(
        TemplateGraphSpecification(
            site=None,
            host_name=HostAddress("h"),
            service_description="svc",
            destination="dashboard",
        ),
        registered_graphs=registered_graphs,
        registered_metrics=registered_metrics,
        fetch_metric_names=_FakeRRDFetchMetricNames(),
    )
    assert isinstance(built.specification, TemplateGraphSpecification)
    assert built.specification.graph_id == "plugin_graph"
    # The id round-trips: replaying the spec yields exactly the graph it was built for.
    assert [
        replayed.graph.name
        for replayed in build_template_graphs(
            built.specification,
            registered_graphs=registered_graphs,
            registered_metrics=registered_metrics,
            fetch_metric_names=_FakeRRDFetchMetricNames(),
        )
    ] == ["plugin_graph"]
    # Narrowing keeps every other seed field, including the add-to destination.
    assert built.specification.destination == "dashboard"


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
