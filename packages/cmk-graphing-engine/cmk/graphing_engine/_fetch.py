#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from cmk.graphing.v1 import metrics as metrics_v1

from ._evaluate import evaluate_graph, EvaluatedGraph
from ._objects import (
    Graph,
    MetricName,
    MetricTranslation,
    PerformanceData,
    RRDMetric,
    RRDMetricData,
    RRDMetricRef,
    RRDMetricWithCF,
    ServiceRef,
    TimeSeries,
)
from ._options import ConsolidationFunction, TimeRange
from ._translate import translate_performance_data


class FetchRRD(Protocol):
    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]: ...

    def time_series(
        self,
        rrd_columns: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, TimeSeries]: ...


@dataclass(frozen=True, kw_only=True)
class GraphRequest:
    time_range: TimeRange
    # The fallback consolidation function for bare RRDMetric columns. May be omitted only when every
    # metric pins its own (RRDMetricWithCF); fetch_time_series enforces this.
    consolidation_function: ConsolidationFunction | None = None
    graph: Graph
    # The translated metric data of the graph's metrics, as produced by discovery. It carries the
    # originals (raw column + scale) used to fetch the time series and the display attributes.
    metric_data: Mapping[RRDMetricRef, RRDMetricData]


def _consolidation_function(metric: RRDMetricRef, request: GraphRequest) -> ConsolidationFunction:
    match metric:
        case RRDMetricWithCF():
            return metric.consolidation_function
        case RRDMetric():
            # A bare metric uses the request's function; fetch_time_series guarantees it is set.
            assert request.consolidation_function is not None
            return request.consolidation_function


def _scaled(time_series: TimeSeries, scale: float) -> TimeSeries:
    if scale == 1.0:
        return time_series
    return TimeSeries(
        time_range=time_series.time_range,
        values=[None if value is None else value * scale for value in time_series.values],
    )


def _merge(series: Sequence[TimeSeries], time_range: TimeRange) -> TimeSeries:
    # Merge a metric's originals point by point, taking the first value present.
    return TimeSeries(
        time_range=time_range,
        values=[
            next((value for value in point if value is not None), None)
            for point in zip(*(member.values for member in series))
        ],
    )


def _fetch_series(request: GraphRequest, rrd: FetchRRD) -> Mapping[RRDMetricRef, TimeSeries]:
    # A metric's originals are the raw RRD columns to read (with per-column scale). Fetch the
    # columns batched by consolidation function (a pinned metric uses its own, a bare one the
    # request's), then scale each column and merge a metric's columns point by point.
    columns_per_metric: dict[
        RRDMetricRef, tuple[ConsolidationFunction, list[tuple[RRDMetric, float]]]
    ]
    columns_per_metric = {}
    columns_per_function: dict[ConsolidationFunction, list[RRDMetric]] = {}
    for metric in request.graph.rrd_metrics():
        if (data := request.metric_data.get(metric)) is None:
            continue
        consolidation_function = _consolidation_function(metric, request)
        columns = [
            (
                RRDMetric(
                    host_name=metric.host_name,
                    service_name=metric.service_name,
                    metric_name=original.metric_name,
                ),
                original.scale,
            )
            for original in data.originals
        ]
        columns_per_metric[metric] = (consolidation_function, columns)
        columns_per_function.setdefault(consolidation_function, []).extend(
            column for column, _scale in columns
        )

    raw_per_function = {
        consolidation_function: rrd.time_series(
            list(dict.fromkeys(columns)),
            time_range=request.time_range,
            consolidation_function=consolidation_function,
        )
        for consolidation_function, columns in columns_per_function.items()
    }

    result: dict[RRDMetricRef, TimeSeries] = {}
    for metric, (consolidation_function, columns) in columns_per_metric.items():
        raw = raw_per_function[consolidation_function]
        scaled = [_scaled(raw[column], scale) for column, scale in columns if column in raw]
        if scaled:
            result[metric] = _merge(scaled, request.time_range)
    return result


def _fetch_and_evaluate(request: GraphRequest, rrd: FetchRRD) -> EvaluatedGraph:
    return evaluate_graph(
        request.graph,
        _fetch_series(request, rrd),
        request.metric_data,
        request.time_range,
    )


def _validate_consolidation_function(request: GraphRequest) -> None:
    # Without a request-level consolidation function, every metric must pin its own.
    if request.consolidation_function is not None:
        return
    bare = [
        metric for metric in request.graph.rrd_metrics() if not isinstance(metric, RRDMetricWithCF)
    ]
    if bare:
        raise ValueError(
            "No consolidation function given and these metrics do not pin one: "
            f"{', '.join(metric.metric_name for metric in bare)}"
        )


def fetch_time_series(
    requests: Sequence[GraphRequest],
    *,
    rrd: FetchRRD,
) -> Sequence[EvaluatedGraph]:
    for request in requests:
        _validate_consolidation_function(request)
    return [_fetch_and_evaluate(request, rrd) for request in requests]


def fetch_translated_metrics(
    services: Iterable[ServiceRef],
    *,
    rrd: FetchRRD,
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
) -> Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]:
    # dict.fromkeys dedups the services while keeping a deterministic order.
    performance_data = rrd.fetch_performance_data(list(dict.fromkeys(services)))
    return {
        service: translate_performance_data(perf, translations, metrics, localizer)
        for service, perf in performance_data.items()
    }
