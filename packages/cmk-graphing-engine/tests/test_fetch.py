#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.graphing_engine import (
    AutoPrecision,
    ConsolidationFunction,
    DecimalNotation,
    Graph,
    GraphRequest,
    Line,
    MetricName,
    PerformanceData,
    Quantity,
    RRDMetric,
    RRDMetricData,
    RRDMetricRef,
    RRDMetricWithCF,
    RRDOriginal,
    ServiceRef,
    TimeRange,
    TimeSeries,
    Unit,
    update_graph_data,
)

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


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


def _source(name: str) -> RRDMetric:
    # The raw RRD column the engine fetches (built from a metric's originals).
    return RRDMetric(host_name="h", service_name="svc", metric_name=MetricName(name))


def _data(metric: RRDMetricRef, *, scale: float = 1.0) -> RRDMetricData:
    return RRDMetricData(
        value=1.0,
        originals=[RRDOriginal(metric_name=metric.metric_name, scale=scale)],
        title=str(metric.metric_name),
        unit=_UNIT,
        color="#28a2f3",
    )


def _request(
    graph: Graph,
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
    *,
    consolidation_function: ConsolidationFunction | None = None,
) -> GraphRequest:
    return GraphRequest(
        graph=graph,
        time_range=_time_range(),
        consolidation_function=consolidation_function,
        metric_data=metric_data,
    )


def _ts(*values: float | None) -> TimeSeries:
    return TimeSeries(time_range=_time_range(), values=list(values))


def _time_series(value: float) -> TimeSeries:
    return _ts(*([value] * 6))


class _FakeFetchRRD:
    def __init__(
        self,
        time_series_response: Mapping[RRDMetric, TimeSeries] | None = None,
    ) -> None:
        self._response = time_series_response or {}
        self.time_series_calls: list[
            tuple[
                tuple[RRDMetric, ...],
                TimeRange,
                ConsolidationFunction,
            ]
        ] = []

    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]:
        raise NotImplementedError

    def time_series(
        self,
        rrd_columns: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.time_series_calls.append((tuple(rrd_columns), time_range, consolidation_function))
        return {
            column: self._response[column] for column in rrd_columns if column in self._response
        }


def test_empty_requests_returns_empty_list() -> None:
    rrd = _FakeFetchRRD()
    assert update_graph_data([], rrd=rrd) == []
    assert rrd.time_series_calls == []


def test_returns_one_evaluated_graph_per_request() -> None:
    cpu_user = _rrd_with_cf("cpu_user")
    cpu_system = _rrd_with_cf("cpu_system")
    cpu_user_time_series = _time_series(1.0)
    cpu_system_time_series = _time_series(2.0)
    graph = Graph(name="cpu", title="CPU", lines=[_line(cpu_user), _line(cpu_system)])
    request = _request(graph, {cpu_user: _data(cpu_user), cpu_system: _data(cpu_system)})
    rrd = _FakeFetchRRD(
        time_series_response={
            _source("cpu_user"): cpu_user_time_series,
            _source("cpu_system"): cpu_system_time_series,
        }
    )

    [evaluated] = update_graph_data([request], rrd=rrd)

    assert evaluated.stacks == []
    assert [line.curve.time_series for line in evaluated.lines] == [
        cpu_user_time_series,
        cpu_system_time_series,
    ]
    # The metrics are pinned to AVERAGE, so their columns are fetched in one batch with it.
    [(columns, time_range, consolidation_function)] = rrd.time_series_calls
    assert set(columns) == {_source("cpu_user"), _source("cpu_system")}
    assert time_range == TimeRange(start=0, end=60, step=10)
    assert consolidation_function is ConsolidationFunction.AVERAGE


def test_fetches_one_batch_per_consolidation_function() -> None:
    avg_metric = _rrd_with_cf("a", ConsolidationFunction.AVERAGE)
    max_metric = _rrd_with_cf("b", ConsolidationFunction.MAX)
    graph = Graph(name="g", title="g", lines=[_line(avg_metric), _line(max_metric)])
    request = _request(graph, {avg_metric: _data(avg_metric), max_metric: _data(max_metric)})
    rrd = _FakeFetchRRD(
        time_series_response={_source("a"): _time_series(1.0), _source("b"): _time_series(2.0)}
    )

    update_graph_data([request], rrd=rrd)

    # One time-series fetch per distinct consolidation function.
    columns_by_cf = {cf: columns for columns, _tr, cf in rrd.time_series_calls}
    assert columns_by_cf == {
        ConsolidationFunction.AVERAGE: (_source("a"),),
        ConsolidationFunction.MAX: (_source("b"),),
    }


def test_multiple_requests_yield_one_evaluated_graph_each_in_order() -> None:
    x = _rrd_with_cf("x")
    y = _rrd_with_cf("y")
    x_time_series = _time_series(1.0)
    y_time_series = _time_series(2.0)
    request_x = _request(Graph(name="x", title="x", lines=[_line(x)]), {x: _data(x)})
    request_y = _request(Graph(name="y", title="y", lines=[_line(y)]), {y: _data(y)})
    rrd = _FakeFetchRRD(
        time_series_response={_source("x"): x_time_series, _source("y"): y_time_series}
    )

    results = update_graph_data([request_x, request_y], rrd=rrd)

    assert [[line.curve.time_series for line in graph.lines] for graph in results] == [
        [x_time_series],
        [y_time_series],
    ]


def test_evaluates_lines_in_both_directions() -> None:
    # A collapsed bidirectional: the upper line normal, the lower line inverse.
    in_ = _rrd_with_cf("if_in")
    out = _rrd_with_cf("if_out")
    in_time_series = _time_series(1.0)
    out_time_series = _time_series(2.0)
    graph = Graph(
        name="if",
        title="Interface",
        lines=[_line(out), Line(quantity=in_, inverse=True)],
    )
    request = _request(graph, {in_: _data(in_), out: _data(out)})
    rrd = _FakeFetchRRD(
        time_series_response={_source("if_in"): in_time_series, _source("if_out"): out_time_series}
    )

    [evaluated] = update_graph_data([request], rrd=rrd)

    assert [(line.curve.time_series, line.inverse) for line in evaluated.lines] == [
        (out_time_series, False),
        (in_time_series, True),
    ]


def test_scales_each_column_by_its_scale() -> None:
    temp = _rrd_with_cf("temp")
    graph = Graph(name="g", title="g", lines=[_line(temp)])
    request = _request(graph, {temp: _data(temp, scale=2.0)})
    rrd = _FakeFetchRRD(time_series_response={_source("temp"): _time_series(10.0)})

    [evaluated] = update_graph_data([request], rrd=rrd)

    # The raw values (10.0) are scaled by the column's scale (2.0).
    [line] = evaluated.lines
    assert line.curve.time_series == _time_series(20.0)


def test_fetches_a_renamed_metric_by_its_raw_column() -> None:
    # The metric is named "temp" but its data comes from the raw column "temperature".
    temp = _rrd_with_cf("temp")
    graph = Graph(name="g", title="g", lines=[_line(temp)])
    metric_data: Mapping[RRDMetricRef, RRDMetricData] = {
        temp: RRDMetricData(
            value=1.0,
            originals=[RRDOriginal(metric_name=MetricName("temperature"), scale=1.0)],
            title="temp",
            unit=_UNIT,
            color="#28a2f3",
        )
    }
    time_series = _time_series(5.0)
    rrd = _FakeFetchRRD(time_series_response={_source("temperature"): time_series})

    [evaluated] = update_graph_data([_request(graph, metric_data)], rrd=rrd)

    [line] = evaluated.lines
    assert line.curve.time_series == time_series
    # The raw column is fetched, not the translated name.
    [(columns, _tr, _cf)] = rrd.time_series_calls
    assert columns == (_source("temperature"),)


def test_merges_a_metrics_originals_taking_the_first_present_value() -> None:
    metric = _rrd_with_cf("m")
    graph = Graph(name="g", title="g", lines=[_line(metric)])
    metric_data: Mapping[RRDMetricRef, RRDMetricData] = {
        metric: RRDMetricData(
            value=1.0,
            originals=[
                RRDOriginal(metric_name=MetricName("a"), scale=1.0),
                RRDOriginal(metric_name=MetricName("b"), scale=1.0),
            ],
            title="m",
            unit=_UNIT,
            color="#28a2f3",
        )
    }
    rrd = _FakeFetchRRD(
        time_series_response={
            _source("a"): _ts(1.0, None, 3.0),
            _source("b"): _ts(None, 2.0, 4.0),
        }
    )

    [evaluated] = update_graph_data([_request(graph, metric_data)], rrd=rrd)

    # Per point, the first present value wins: a where it has data, otherwise b.
    [line] = evaluated.lines
    assert line.curve.time_series == _ts(1.0, 2.0, 3.0)


def test_bare_metric_adopts_the_request_consolidation_function() -> None:
    # A bare RRDMetric uses the request's function; a pinned RRDMetricWithCF keeps its own.
    bare = RRDMetric(host_name="h", service_name="svc", metric_name=MetricName("load"))
    pinned = _rrd_with_cf("peak", ConsolidationFunction.MAX)
    graph = Graph(name="g", title="g", lines=[_line(bare), _line(pinned)])
    request = _request(
        graph,
        {bare: _data(bare), pinned: _data(pinned)},
        consolidation_function=ConsolidationFunction.AVERAGE,
    )
    rrd = _FakeFetchRRD(
        time_series_response={
            _source("load"): _time_series(1.0),
            _source("peak"): _time_series(2.0),
        }
    )

    update_graph_data([request], rrd=rrd)

    columns_by_cf = {cf: columns for columns, _tr, cf in rrd.time_series_calls}
    assert columns_by_cf == {
        ConsolidationFunction.AVERAGE: (_source("load"),),
        ConsolidationFunction.MAX: (_source("peak"),),
    }


def test_evaluates_without_a_request_consolidation_function_when_every_metric_pins_one() -> None:
    # No request-level function is needed: the pinned metric carries its own.
    pinned = _rrd_with_cf("temp", ConsolidationFunction.MAX)
    graph = Graph(name="g", title="g", lines=[_line(pinned)])
    request = _request(graph, {pinned: _data(pinned)})
    rrd = _FakeFetchRRD(time_series_response={_source("temp"): _time_series(1.0)})

    [evaluated] = update_graph_data([request], rrd=rrd)

    assert [line.curve.time_series for line in evaluated.lines] == [_time_series(1.0)]
    [(_columns, _tr, consolidation_function)] = rrd.time_series_calls
    assert consolidation_function is ConsolidationFunction.MAX


def test_rejects_a_bare_metric_without_a_request_consolidation_function() -> None:
    bare = RRDMetric(host_name="h", service_name="svc", metric_name=MetricName("load"))
    graph = Graph(name="g", title="g", lines=[_line(bare)])
    request = _request(graph, {bare: _data(bare)})

    with pytest.raises(ValueError, match="load"):
        update_graph_data([request], rrd=_FakeFetchRRD())
