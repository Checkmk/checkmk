#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing_engine import (
    ConsolidationFunction,
    fetch_time_series,
    Graph,
    GraphRequest,
    Line,
    MetricName,
    PerformanceDataByService,
    Quantity,
    RRDMetric,
    RRDMetricRef,
    RRDMetricWithCF,
    ServiceRef,
    TimeRange,
    TimeSeries,
)


def _line(quantity: Quantity) -> Line:
    return Line(quantity=quantity, inverse=False)


def _time_range() -> TimeRange:
    return TimeRange(start=0, end=60, step=10)


def _rrd_with_cf(
    name: str,
    consolidation_function: ConsolidationFunction = ConsolidationFunction.AVERAGE,
) -> RRDMetricWithCF:
    return RRDMetricWithCF(
        host_name="h",
        service_name="svc",
        metric_name=MetricName(name),
        consolidation_function=consolidation_function,
    )


def _series(value: float) -> TimeSeries:
    return TimeSeries(
        time_range=TimeRange(start=0, end=60, step=10),
        values=[value] * 6,
    )


class _FakeFetchRRD:
    def __init__(
        self,
        time_series_response: Mapping[RRDMetricRef, TimeSeries] | None = None,
    ) -> None:
        self._response = time_series_response or {}
        self.time_series_calls: list[
            tuple[
                tuple[RRDMetricRef, ...],
                TimeRange,
                ConsolidationFunction,
            ]
        ] = []

    def fetch_performance_data(self, services: Sequence[ServiceRef]) -> PerformanceDataByService:
        raise NotImplementedError

    def time_series(
        self,
        rrd_metrics: Sequence[RRDMetricRef],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetricRef, TimeSeries]:
        self.time_series_calls.append((tuple(rrd_metrics), time_range, consolidation_function))
        return {
            metric: self._response[metric] for metric in rrd_metrics if metric in self._response
        }


def test_empty_requests_returns_empty_list() -> None:
    rrd = _FakeFetchRRD()
    assert fetch_time_series([], rrd=rrd) == []
    assert rrd.time_series_calls == []


def test_returns_one_data_mapping_per_request_keyed_by_rrd_metric() -> None:
    cpu_user = _rrd_with_cf("cpu_user")
    cpu_system = _rrd_with_cf("cpu_system")
    cpu_user_series = _series(1.0)
    cpu_system_series = _series(2.0)
    graph = Graph(name="cpu", title="CPU", simple_lines=[_line(cpu_user), _line(cpu_system)])
    request = GraphRequest(
        graph=graph, time_range=_time_range(), consolidation_function=ConsolidationFunction.MAX
    )
    rrd = _FakeFetchRRD(
        time_series_response={
            cpu_user: cpu_user_series,
            cpu_system: cpu_system_series,
        }
    )

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {cpu_user: cpu_user_series, cpu_system: cpu_system_series}
    [(metrics_arg, time_range, consolidation_function)] = rrd.time_series_calls
    assert set(metrics_arg) == {cpu_user, cpu_system}
    assert time_range == TimeRange(start=0, end=60, step=10)
    assert consolidation_function is ConsolidationFunction.AVERAGE


def test_fetches_one_batch_per_consolidation_function() -> None:
    avg_metric = _rrd_with_cf("a", ConsolidationFunction.AVERAGE)
    max_metric = _rrd_with_cf("b", ConsolidationFunction.MAX)
    avg_series = _series(1.0)
    max_series = _series(2.0)
    graph = Graph(name="g", title="g", simple_lines=[_line(avg_metric), _line(max_metric)])
    request = GraphRequest(
        graph=graph, time_range=_time_range(), consolidation_function=ConsolidationFunction.MAX
    )
    rrd = _FakeFetchRRD(time_series_response={avg_metric: avg_series, max_metric: max_series})

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {avg_metric: avg_series, max_metric: max_series}
    # One fetch per distinct consolidation function.
    metrics_by_cf = {cf: metrics for metrics, _tr, cf in rrd.time_series_calls}
    assert metrics_by_cf == {
        ConsolidationFunction.AVERAGE: (avg_metric,),
        ConsolidationFunction.MAX: (max_metric,),
    }


def test_multiple_requests_yield_one_mapping_each_in_order() -> None:
    x = _rrd_with_cf("x")
    y = _rrd_with_cf("y")
    x_series = _series(1.0)
    y_series = _series(2.0)
    graph_x = Graph(name="x", title="x", simple_lines=[_line(x)])
    graph_y = Graph(name="y", title="y", simple_lines=[_line(y)])
    request_x = GraphRequest(
        graph=graph_x, time_range=_time_range(), consolidation_function=ConsolidationFunction.MAX
    )
    request_y = GraphRequest(
        graph=graph_y, time_range=_time_range(), consolidation_function=ConsolidationFunction.MAX
    )
    rrd = _FakeFetchRRD(time_series_response={x: x_series, y: y_series})

    results = fetch_time_series([request_x, request_y], rrd=rrd)

    assert results == [{x: x_series}, {y: y_series}]


def test_fetches_metrics_from_both_halves_of_a_bidirectional() -> None:
    in_ = _rrd_with_cf("if_in")
    out = _rrd_with_cf("if_out")
    in_series = _series(1.0)
    out_series = _series(2.0)
    graph = Graph(
        name="if",
        title="Interface",
        simple_lines=[_line(out), Line(quantity=in_, inverse=True)],
    )
    request = GraphRequest(
        graph=graph, time_range=_time_range(), consolidation_function=ConsolidationFunction.MAX
    )
    rrd = _FakeFetchRRD(time_series_response={in_: in_series, out: out_series})

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {in_: in_series, out: out_series}


def test_bare_metric_adopts_the_request_consolidation_function() -> None:
    # A bare RRDMetric uses the request's function; a pinned RRDMetricWithCF keeps its own.
    bare = RRDMetric(host_name="h", service_name="svc", metric_name=MetricName("load"))
    pinned = _rrd_with_cf("peak", ConsolidationFunction.MAX)
    bare_series = _series(1.0)
    peak_series = _series(2.0)
    graph = Graph(name="g", title="g", simple_lines=[_line(bare), _line(pinned)])
    request = GraphRequest(
        graph=graph, time_range=_time_range(), consolidation_function=ConsolidationFunction.AVERAGE
    )
    rrd = _FakeFetchRRD(time_series_response={bare: bare_series, pinned: peak_series})

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {bare: bare_series, pinned: peak_series}
    metrics_by_cf = {cf: metrics for metrics, _tr, cf in rrd.time_series_calls}
    assert metrics_by_cf == {
        ConsolidationFunction.AVERAGE: (bare,),
        ConsolidationFunction.MAX: (pinned,),
    }
