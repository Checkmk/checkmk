#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing_engine import (
    ConsolidationFunction,
    discover_explicit_graphs,
    ExplicitDiscoveryOptions,
    ExplicitOptions,
    FixedRange,
    Graph,
    Line,
    MetricName,
    PerformanceData,
    PerformanceValue,
    Quantity,
    RRDMetric,
    RRDMetricWithCF,
    ServiceRef,
    TimeRange,
    TimeSeries,
    WarningOf,
)


def _id(s: str) -> str:
    return s


def _metric(name: str, title: Title) -> metrics_v1.Metric:
    return metrics_v1.Metric(
        name=name,
        title=title,
        unit=metrics_v1.Unit(metrics_v1.DecimalNotation("")),
        color=metrics_v1.Color.BLUE,
    )


_METRICS = {
    "cpu_user": _metric("cpu_user", Title("CPU user")),
    "cpu_system": _metric("cpu_system", Title("CPU system")),
    "if_in": _metric("if_in", Title("If in")),
    "if_out": _metric("if_out", Title("If out")),
    "load": _metric("load", Title("Load")),
}


def _time_range() -> TimeRange:
    return TimeRange(start=0, end=60, step=10)


def _service() -> ServiceRef:
    return ServiceRef(host_name="h", service_name="svc")


def _line(quantity: Quantity) -> Line:
    return Line(quantity=quantity, inverse=False)


def _options(graph: Graph) -> ExplicitDiscoveryOptions:
    return ExplicitDiscoveryOptions(
        time_range=_time_range(),
        graph=graph,
        localizer=_id,
        metrics=_METRICS,
        translations={},
    )


def _rrd(name: MetricName) -> RRDMetricWithCF:
    return RRDMetricWithCF(
        host_name="h",
        service_name="svc",
        metric_name=name,
        consolidation_function=ConsolidationFunction.AVERAGE,
    )


def _perf(
    name: MetricName,
    *,
    value: float,
    warning: float | None = None,
    critical: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> PerformanceValue:
    return PerformanceValue(
        metric_name=name,
        value=value,
        warning=warning,
        critical=critical,
        minimum=minimum,
        maximum=maximum,
    )


def _perf_data(*values: PerformanceValue) -> PerformanceData:
    return PerformanceData(check_command="", values=list(values))


class _FakeFetchRRD:
    def __init__(
        self,
        performance_response: Mapping[ServiceRef, PerformanceData] | None = None,
        time_series_response: Mapping[RRDMetric, TimeSeries] | None = None,
    ) -> None:
        self._performance_response = performance_response or {}
        self._time_series_response = time_series_response or {}
        self.performance_data_calls: list[tuple[ServiceRef, ...]] = []
        self.time_series_calls: list[
            tuple[tuple[RRDMetric, ...], TimeRange, ConsolidationFunction]
        ] = []

    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]:
        self.performance_data_calls.append(tuple(services))
        return self._performance_response

    def fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.time_series_calls.append((tuple(rrd_metrics), time_range, consolidation_function))
        return {
            metric: self._time_series_response[metric]
            for metric in rrd_metrics
            if metric in self._time_series_response
        }


def test_discover_explicit_graphs_without_keys_returns_inline_definition_unchanged() -> None:
    inline = Graph(name="g", title="t")
    options = _options(inline)
    rrd = _FakeFetchRRD()

    rendered = discover_explicit_graphs(options, rrd=rrd)

    assert len(rendered) == 1
    assert rendered[0].graph is inline
    assert rendered[0].options == ExplicitOptions(time_range=_time_range())
    assert rendered[0].title == "t"
    assert rendered[0].stacks == []
    assert rendered[0].lines == []


def test_discover_explicit_graphs_carries_scalars_for_referenced_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    inline = Graph(
        name="cpu",
        title="CPU",
        # cpu_user as a curve; cpu_system referenced only by a scalar threshold.
        lines=[
            _line(_rrd(cpu_user)),
            _line(WarningOf(metric=_rrd(cpu_system), color="#28a2f3")),
        ],
    )
    options = _options(inline)
    rrd = _FakeFetchRRD(
        performance_response={
            service: _perf_data(
                _perf(cpu_user, value=42.0, warning=80.0, critical=90.0),
                _perf(
                    cpu_system, value=8.0, warning=50.0, critical=70.0, minimum=0.0, maximum=100.0
                ),
            )
        },
    )

    [rendered] = discover_explicit_graphs(options, rrd=rrd)

    # cpu_user is drawn with its value; the threshold curve takes cpu_system's warning as its value.
    assert [(line.curve.title, line.curve.value) for line in rendered.lines] == [
        ("CPU user", 42.0),
        ("CPU system", 50.0),
    ]
    assert rrd.performance_data_calls == [(service,)]


def test_discover_explicit_graphs_omits_scalars_for_metrics_not_in_translated_metrics() -> None:
    service = _service()
    inline = Graph(name="g", title="g", lines=[_line(_rrd(MetricName("missing_metric")))])
    options = _options(inline)
    rrd = _FakeFetchRRD(performance_response={service: _perf_data()})

    [rendered] = discover_explicit_graphs(options, rrd=rrd)

    # The metric has no data, so its curve is dropped from the evaluated graph.
    assert rendered.title == "g"
    assert rendered.stacks == []
    assert rendered.lines == []


def test_discover_explicit_graphs_carries_scalars_across_a_bidirectional() -> None:
    service = _service()
    if_in = MetricName("if_in")
    if_out = MetricName("if_out")
    inline = Graph(
        name="if",
        title="Interface",
        lines=[_line(_rrd(if_out)), Line(quantity=_rrd(if_in), inverse=True)],
    )
    options = _options(inline)
    rrd = _FakeFetchRRD(
        performance_response={
            service: _perf_data(_perf(if_in, value=1.0, warning=10.0), _perf(if_out, value=2.0))
        }
    )

    [rendered] = discover_explicit_graphs(options, rrd=rrd)

    # Upper line normal, lower line inverse; each curve carries its metric's value.
    assert [(line.curve.title, line.curve.value, line.inverse) for line in rendered.lines] == [
        ("If out", 2.0, False),
        ("If in", 1.0, True),
    ]


def test_discover_explicit_graphs_keeps_same_metric_name_on_different_services_distinct() -> None:
    # Two services expose a metric with the same name; each curve must resolve to its own service's
    # data rather than colliding on the bare metric name.
    service_a = ServiceRef(host_name="host-a", service_name="svc")
    service_b = ServiceRef(host_name="host-b", service_name="svc")
    load = MetricName("load")
    metric_a = RRDMetricWithCF(
        host_name="host-a",
        service_name="svc",
        metric_name=load,
        consolidation_function=ConsolidationFunction.AVERAGE,
    )
    metric_b = RRDMetricWithCF(
        host_name="host-b",
        service_name="svc",
        metric_name=load,
        consolidation_function=ConsolidationFunction.AVERAGE,
    )
    inline = Graph(name="load", title="Load", lines=[_line(metric_a), _line(metric_b)])
    options = _options(inline)
    rrd = _FakeFetchRRD(
        performance_response={
            service_a: _perf_data(_perf(load, value=1.0)),
            service_b: _perf_data(_perf(load, value=2.0)),
        }
    )

    [rendered] = discover_explicit_graphs(options, rrd=rrd)

    # Same metric name, same title - distinguished by the per-service value.
    assert [(line.curve.title, line.curve.value) for line in rendered.lines] == [
        ("Load", 1.0),
        ("Load", 2.0),
    ]


def test_discover_explicit_graphs_passes_through_a_fixed_vertical_range() -> None:
    service = _service()
    inline = Graph(
        name="g",
        title="g",
        vertical_range=FixedRange(lower=0, upper=100),
        lines=[_line(_rrd(MetricName("a")))],
    )
    options = _options(inline)
    rrd = _FakeFetchRRD(performance_response={service: _perf_data()})

    [rendered] = discover_explicit_graphs(options, rrd=rrd)

    assert rendered.graph is inline
    assert isinstance(rendered.graph, Graph)
    assert rendered.graph.vertical_range == FixedRange(lower=0, upper=100)
