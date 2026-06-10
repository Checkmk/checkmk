#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing_engine import (
    AutoPrecision,
    Bidirectional,
    CommonOptions,
    ConsolidationFunction,
    DecimalNotation,
    fetch_time_series,
    Graph,
    GraphRequest,
    Metric,
    MetricName,
    RRDMetric,
    RRDMetricData,
    RRDOriginal,
    ServiceRef,
    TemperatureUnit,
    TimeRange,
    TimeSeries,
    Unit,
)


def _common() -> CommonOptions:
    return CommonOptions(
        time_range=TimeRange(start=0, end=60, step=10),
        temperature_unit=TemperatureUnit.CELSIUS,
    )


def _rrd(
    name: str,
    consolidation_function: ConsolidationFunction = ConsolidationFunction.AVERAGE,
) -> RRDMetric:
    return RRDMetric(
        host_name="h",
        service_name="svc",
        metric_name=MetricName(name),
        consolidation_function=consolidation_function,
    )


def _line(rrd: RRDMetric) -> Metric:
    return Metric(
        rrd_metric=rrd,
        title=rrd.metric_name,
        unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
        color="#28a2f3",
    )


def _series(value: float) -> TimeSeries:
    return TimeSeries(
        time_range=TimeRange(start=0, end=60, step=10),
        values=[value] * 6,
    )


class _FakeFetchRRD:
    def __init__(
        self,
        time_series_response: Mapping[RRDOriginal, TimeSeries] | None = None,
    ) -> None:
        self._response = time_series_response or {}
        self.time_series_calls: list[
            tuple[
                tuple[RRDOriginal, ...],
                TimeRange,
                ConsolidationFunction,
            ]
        ] = []

    def translated_metrics(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]:
        raise NotImplementedError

    def time_series(
        self,
        keys: Sequence[RRDOriginal],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDOriginal, TimeSeries]:
        self.time_series_calls.append((tuple(keys), time_range, consolidation_function))
        return {key: self._response[key] for key in keys if key in self._response}


def test_empty_requests_returns_empty_list() -> None:
    rrd = _FakeFetchRRD()
    assert fetch_time_series([], rrd=rrd) == []
    assert rrd.time_series_calls == []


def test_returns_one_data_mapping_per_request_keyed_by_rrd_metric() -> None:
    cpu_user = _rrd("cpu_user")
    cpu_system = _rrd("cpu_system")
    cpu_user_key = RRDOriginal(metric_name=cpu_user.metric_name, scale=1.0)
    cpu_system_key = RRDOriginal(metric_name=cpu_system.metric_name, scale=1.0)
    cpu_user_series = _series(1.0)
    cpu_system_series = _series(2.0)
    graph = Graph(name="cpu", title="CPU", simple_lines=[_line(cpu_user), _line(cpu_system)])
    request = GraphRequest(graph=graph, common=_common())
    rrd = _FakeFetchRRD(
        time_series_response={
            cpu_user_key: cpu_user_series,
            cpu_system_key: cpu_system_series,
        }
    )

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {cpu_user: cpu_user_series, cpu_system: cpu_system_series}
    [(keys_arg, time_range, consolidation_function)] = rrd.time_series_calls
    assert set(keys_arg) == {cpu_user_key, cpu_system_key}
    assert time_range == TimeRange(start=0, end=60, step=10)
    assert consolidation_function is ConsolidationFunction.AVERAGE


def test_fetches_one_batch_per_consolidation_function() -> None:
    avg_metric = _rrd("a", ConsolidationFunction.AVERAGE)
    max_metric = _rrd("b", ConsolidationFunction.MAX)
    avg_key = RRDOriginal(metric_name=MetricName("a"), scale=1.0)
    max_key = RRDOriginal(metric_name=MetricName("b"), scale=1.0)
    avg_series = _series(1.0)
    max_series = _series(2.0)
    graph = Graph(name="g", title="g", simple_lines=[_line(avg_metric), _line(max_metric)])
    request = GraphRequest(graph=graph, common=_common())
    rrd = _FakeFetchRRD(time_series_response={avg_key: avg_series, max_key: max_series})

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {avg_metric: avg_series, max_metric: max_series}
    # One fetch per distinct consolidation function.
    keys_by_cf = {cf: keys for keys, _tr, cf in rrd.time_series_calls}
    assert keys_by_cf == {
        ConsolidationFunction.AVERAGE: (avg_key,),
        ConsolidationFunction.MAX: (max_key,),
    }


def test_multiple_requests_yield_one_mapping_each_in_order() -> None:
    x = _rrd("x")
    y = _rrd("y")
    x_key = RRDOriginal(metric_name=x.metric_name, scale=1.0)
    y_key = RRDOriginal(metric_name=y.metric_name, scale=1.0)
    x_series = _series(1.0)
    y_series = _series(2.0)
    graph_x = Graph(name="x", title="x", simple_lines=[_line(x)])
    graph_y = Graph(name="y", title="y", simple_lines=[_line(y)])
    request_x = GraphRequest(graph=graph_x, common=_common())
    request_y = GraphRequest(graph=graph_y, common=_common())
    rrd = _FakeFetchRRD(time_series_response={x_key: x_series, y_key: y_series})

    results = fetch_time_series([request_x, request_y], rrd=rrd)

    assert results == [{x: x_series}, {y: y_series}]


def test_fetches_metrics_from_both_halves_of_a_bidirectional() -> None:
    in_ = _rrd("if_in")
    out = _rrd("if_out")
    in_key = RRDOriginal(metric_name=in_.metric_name, scale=1.0)
    out_key = RRDOriginal(metric_name=out.metric_name, scale=1.0)
    in_series = _series(1.0)
    out_series = _series(2.0)
    graph = Bidirectional(
        name="if",
        title="Interface",
        lower=Graph(name="in", title="In", simple_lines=[_line(in_)]),
        upper=Graph(name="out", title="Out", simple_lines=[_line(out)]),
    )
    request = GraphRequest(graph=graph, common=_common())
    rrd = _FakeFetchRRD(time_series_response={in_key: in_series, out_key: out_series})

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {in_: in_series, out: out_series}
