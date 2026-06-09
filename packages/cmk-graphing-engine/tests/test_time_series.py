#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing_engine import (
    CommonOptions,
    ConsolidationFunction,
    fetch_time_series,
    Graph,
    GraphRequest,
    MetricName,
    RRDMetric,
    RRDSource,
    ServiceRef,
    TemperatureUnit,
    TimeRange,
    TimeSeries,
    TranslatedMetric,
)


def _common() -> CommonOptions:
    return CommonOptions(
        time_range=TimeRange(start=0, end=60, step=10),
        temperature_unit=TemperatureUnit.CELSIUS,
    )


def _service() -> ServiceRef:
    return ServiceRef(site_id="s", host_name="h", service_name="svc")


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


def _series(value: float) -> TimeSeries:
    return TimeSeries(
        time_range=TimeRange(start=0, end=60, step=10),
        values=[value] * 6,
    )


class _FakeFetchRRD:
    def __init__(
        self,
        time_series_response: Mapping[RRDSource, TimeSeries] | None = None,
    ) -> None:
        self._response = time_series_response or {}
        self.time_series_calls: list[
            tuple[
                tuple[RRDSource, ...],
                TimeRange,
                ConsolidationFunction,
            ]
        ] = []

    def translated_metrics(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, Mapping[MetricName, TranslatedMetric]]:
        raise NotImplementedError

    def time_series(
        self,
        keys: Sequence[RRDSource],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDSource, TimeSeries]:
        self.time_series_calls.append((tuple(keys), time_range, consolidation_function))
        return {key: self._response[key] for key in keys if key in self._response}


def test_empty_requests_returns_empty_list() -> None:
    rrd = _FakeFetchRRD()
    assert fetch_time_series([], rrd=rrd) == []
    assert rrd.time_series_calls == []


def test_returns_one_data_mapping_per_request_keyed_by_rrd_metric() -> None:
    service = _service()
    cpu_user = _rrd("cpu_user")
    cpu_system = _rrd("cpu_system")
    cpu_user_key = RRDSource(service=service, metric_name=cpu_user.metric_name, scale=1.0)
    cpu_system_key = RRDSource(service=service, metric_name=cpu_system.metric_name, scale=1.0)
    cpu_user_series = _series(1.0)
    cpu_system_series = _series(2.0)
    graph = Graph(name="cpu", title="CPU", simple_lines=[cpu_user, cpu_system])
    request = GraphRequest(graph=graph, common=_common(), service=service)
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


def test_builds_sources_from_per_metric_host_and_service() -> None:
    service = _service()
    other = RRDMetric(
        host_name="other-host",
        service_name="other-service",
        metric_name=MetricName("m"),
        consolidation_function=ConsolidationFunction.AVERAGE,
    )
    # The fetched source keeps the request's site but uses the metric's own host and service.
    other_key = RRDSource(
        service=ServiceRef(site_id="s", host_name="other-host", service_name="other-service"),
        metric_name=MetricName("m"),
        scale=1.0,
    )
    other_series = _series(3.0)
    graph = Graph(name="g", title="g", simple_lines=[other])
    request = GraphRequest(graph=graph, common=_common(), service=service)
    rrd = _FakeFetchRRD(time_series_response={other_key: other_series})

    [data] = fetch_time_series([request], rrd=rrd)

    assert data == {other: other_series}
    [(keys_arg, _time_range, _cf)] = rrd.time_series_calls
    assert keys_arg == (other_key,)


def test_fetches_one_batch_per_consolidation_function() -> None:
    service = _service()
    avg_metric = _rrd("a", ConsolidationFunction.AVERAGE)
    max_metric = _rrd("b", ConsolidationFunction.MAX)
    avg_key = RRDSource(service=service, metric_name=MetricName("a"), scale=1.0)
    max_key = RRDSource(service=service, metric_name=MetricName("b"), scale=1.0)
    avg_series = _series(1.0)
    max_series = _series(2.0)
    graph = Graph(name="g", title="g", simple_lines=[avg_metric, max_metric])
    request = GraphRequest(graph=graph, common=_common(), service=service)
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
    service = _service()
    x = _rrd("x")
    y = _rrd("y")
    x_key = RRDSource(service=service, metric_name=x.metric_name, scale=1.0)
    y_key = RRDSource(service=service, metric_name=y.metric_name, scale=1.0)
    x_series = _series(1.0)
    y_series = _series(2.0)
    graph_x = Graph(name="x", title="x", simple_lines=[x])
    graph_y = Graph(name="y", title="y", simple_lines=[y])
    request_x = GraphRequest(graph=graph_x, common=_common(), service=service)
    request_y = GraphRequest(graph=graph_y, common=_common(), service=service)
    rrd = _FakeFetchRRD(time_series_response={x_key: x_series, y_key: y_series})

    results = fetch_time_series([request_x, request_y], rrd=rrd)

    assert results == [{x: x_series}, {y: y_series}]
