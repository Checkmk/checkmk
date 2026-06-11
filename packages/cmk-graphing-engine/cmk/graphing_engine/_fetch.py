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
    metric_data_of,
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


class RRDSource(Protocol):
    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]: ...

    def fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, TimeSeries]: ...


@dataclass(frozen=True, kw_only=True)
class GraphRequest:
    graph: Graph
    # The fallback consolidation function for the graph's bare RRDMetric columns. May be omitted
    # only when every metric pins its own (RRDMetricWithCF); update_graph_data enforces this.
    consolidation_function: ConsolidationFunction | None = None


def _consolidation_function(
    metric: RRDMetricRef, consolidation_function: ConsolidationFunction | None
) -> ConsolidationFunction:
    match metric:
        case RRDMetricWithCF():
            return metric.consolidation_function
        case RRDMetric():
            # A bare metric uses the fallback; update_graph_data guarantees it is set.
            assert consolidation_function is not None
            return consolidation_function


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


def _fetch_series(
    graph: Graph,
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
    *,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction | None,
    rrd: RRDSource,
) -> Mapping[RRDMetricRef, TimeSeries]:
    # A metric's originals are the raw RRD metrics to read (with per-metric scale). Fetch them
    # batched by consolidation function (a pinned metric uses its own, a bare one the fallback),
    # then scale each one and merge a metric's series point by point.
    rrd_metrics_per_metric: dict[
        RRDMetricRef, tuple[ConsolidationFunction, list[tuple[RRDMetric, float]]]
    ]
    rrd_metrics_per_metric = {}
    rrd_metrics_per_function: dict[ConsolidationFunction, list[RRDMetric]] = {}
    for metric in graph.rrd_metrics():
        if (data := metric_data.get(metric)) is None:
            continue
        function = _consolidation_function(metric, consolidation_function)
        rrd_metrics = [
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
        rrd_metrics_per_metric[metric] = (function, rrd_metrics)
        rrd_metrics_per_function.setdefault(function, []).extend(
            rrd_metric for rrd_metric, _scale in rrd_metrics
        )

    raw_per_function = {
        function: rrd.fetch_time_series(
            list(dict.fromkeys(rrd_metrics)),
            time_range=time_range,
            consolidation_function=function,
        )
        for function, rrd_metrics in rrd_metrics_per_function.items()
    }

    result: dict[RRDMetricRef, TimeSeries] = {}
    for metric, (function, rrd_metrics) in rrd_metrics_per_metric.items():
        raw = raw_per_function[function]
        scaled = [
            _scaled(raw[rrd_metric], scale)
            for rrd_metric, scale in rrd_metrics
            if rrd_metric in raw
        ]
        if scaled:
            result[metric] = _merge(scaled, time_range)
    return result


def _validate_consolidation_function(
    graph: Graph, consolidation_function: ConsolidationFunction | None
) -> None:
    # Without a fallback consolidation function, every metric must pin its own.
    if consolidation_function is not None:
        return
    bare = [metric for metric in graph.rrd_metrics() if not isinstance(metric, RRDMetricWithCF)]
    if bare:
        raise ValueError(
            "No consolidation function given and these metrics do not pin one: "
            f"{', '.join(metric.metric_name for metric in bare)}"
        )


def fetch_translated_metrics(
    services: Iterable[ServiceRef],
    *,
    rrd: RRDSource,
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


def evaluate_graphs(
    requests: Sequence[GraphRequest],
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
    *,
    time_range: TimeRange,
    rrd: RRDSource,
) -> Sequence[EvaluatedGraph]:
    """Fetch the time series of the requested graphs (given their already translated metrics).

    Each request pairs a graph with the fallback consolidation function for its bare RRDMetric
    columns. Without one, every metric of that graph must pin its own (RRDMetricWithCF); a bare
    RRDMetric without one raises ValueError.
    """
    for request in requests:
        _validate_consolidation_function(request.graph, request.consolidation_function)
    evaluated = []
    for request in requests:
        metric_data = metric_data_of(request.graph, translated_metrics)
        evaluated.append(
            evaluate_graph(
                request.graph,
                _fetch_series(
                    request.graph,
                    metric_data,
                    time_range=time_range,
                    consolidation_function=request.consolidation_function,
                    rrd=rrd,
                ),
                metric_data,
                time_range,
            )
        )
    return evaluated


def update_graph_data(
    requests: Sequence[GraphRequest],
    *,
    time_range: TimeRange,
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    rrd: RRDSource,
) -> Sequence[EvaluatedGraph]:
    """Fetch and evaluate the current performance data and time series of the requested graphs."""
    # Each metric carries its own service; fetch and translate the performance data of all of them.
    translated_metrics = fetch_translated_metrics(
        (
            ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
            for request in requests
            for metric in request.graph.rrd_metrics()
        ),
        rrd=rrd,
        translations=translations,
        metrics=metrics,
        localizer=localizer,
    )
    return evaluate_graphs(requests, translated_metrics, time_range=time_range, rrd=rrd)
