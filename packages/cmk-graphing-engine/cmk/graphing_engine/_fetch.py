#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1

from ._evaluate import evaluate_graph, EvaluatedGraph
from ._from_api import parse_translations_from_api
from ._objects import (
    Graph,
    metric_data_of,
    MetricName,
    PerformanceData,
    RRDMetric,
    RRDMetricData,
    RRDMetricRef,
    RRDMetricWithCF,
    ServiceRef,
    TimeSeries,
)
from ._options import ConsolidationFunction, TimeRange
from ._resample import resample
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
    ) -> Mapping[RRDMetric, TimeSeries]:
        """Read the raw RRD series of the given metrics.

        The series may be returned on their native RRD grid (whatever start/end/step RRDTool
        serves); the engine aligns them to the requested time_range itself. Missing metrics are
        omitted from the result.
        """
        ...


def _consolidation_function(
    metric: RRDMetricRef, consolidation_function: ConsolidationFunction
) -> ConsolidationFunction:
    match metric:
        case RRDMetricWithCF():
            return metric.consolidation_function
        case RRDMetric():
            # A bare metric uses the fallback.
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
    consolidation_function: ConsolidationFunction,
    rrd: RRDSource,
) -> Mapping[RRDMetricRef, TimeSeries]:
    # A metric's originals are the raw RRD metrics to read (with per-metric scale). Fetch them
    # batched by consolidation function (a pinned metric uses its own, a bare one the fallback),
    # then scale each one and merge a metric's series point by point.
    rrd_metrics_per_metric: dict[
        RRDMetricRef, tuple[ConsolidationFunction, list[tuple[RRDMetric, float]]]
    ] = {}
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
        # Align every fetched series to the requested grid before scaling and merging: the source
        # may return its own RRD grid, but the originals are merged point by point.
        scaled = [
            _scaled(resample(raw[rrd_metric], time_range, function), scale)
            for rrd_metric, scale in rrd_metrics
            if rrd_metric in raw
        ]
        if scaled:
            result[metric] = _merge(scaled, time_range)
    return result


def fetch_translated_metrics(
    *,
    # subject
    services: Iterable[ServiceRef],
    # environment
    translations: Iterable[translations_v1.Translation],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    # source
    rrd: RRDSource,
) -> Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]:
    # Parse the registered translation plugins once into the per-check-command lookup.
    parsed_translations = parse_translations_from_api(translations)
    # dict.fromkeys dedups the services while keeping a deterministic order.
    performance_data = rrd.fetch_performance_data(list(dict.fromkeys(services)))
    return {
        service: translate_performance_data(perf, parsed_translations, metrics, localizer)
        for service, perf in performance_data.items()
    }


def evaluate_graphs(
    *,
    # subject
    graphs: Sequence[Graph],
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
    # runtime
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    # source
    rrd: RRDSource,
) -> Sequence[EvaluatedGraph]:
    """Fetch the time series of the given graphs (given their already translated metrics).

    The consolidation function is the fallback for the graphs' bare RRDMetric columns; metrics that
    pin their own (RRDMetricWithCF) keep it.
    """
    evaluated = []
    for graph in graphs:
        metric_data = metric_data_of(graph, translated_metrics)
        evaluated.append(
            evaluate_graph(
                graph,
                _fetch_series(
                    graph,
                    metric_data,
                    time_range=time_range,
                    consolidation_function=consolidation_function,
                    rrd=rrd,
                ),
                metric_data,
                translated_metrics,
                time_range,
            )
        )
    return evaluated


def update_graph_data(
    *,
    # subject
    graphs: Sequence[Graph],
    # environment
    translations: Iterable[translations_v1.Translation],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    # runtime
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    # source
    rrd: RRDSource,
) -> Sequence[EvaluatedGraph]:
    """Fetch and evaluate the current performance data and time series of the given graphs.

    The consolidation function is the fallback for the graphs' bare RRDMetric columns; metrics that
    pin their own (RRDMetricWithCF) keep it.
    """
    # Each metric carries its own service; fetch and translate the performance data of all of them.
    translated_metrics = fetch_translated_metrics(
        services=(
            ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
            for graph in graphs
            for metric in graph.rrd_metrics()
        ),
        translations=translations,
        metrics=metrics,
        localizer=localizer,
        rrd=rrd,
    )
    return evaluate_graphs(
        graphs=graphs,
        translated_metrics=translated_metrics,
        consolidation_function=consolidation_function,
        time_range=time_range,
        rrd=rrd,
    )
