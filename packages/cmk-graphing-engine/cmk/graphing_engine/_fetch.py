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
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[RRDMetric, TimeSeries]: ...


def _consolidation_function(
    metric: RRDMetricRef, consolidation_function: ConsolidationFunction
) -> ConsolidationFunction:
    match metric:
        case RRDMetricWithCF():
            return metric.consolidation_function
        case RRDMetric():
            return consolidation_function


def _scaled(time_series: TimeSeries, scale: float) -> TimeSeries:
    if scale == 1.0:
        return time_series
    return TimeSeries(
        time_range=time_series.time_range,
        values=[None if value is None else value * scale for value in time_series.values],
    )


def _merge(series: Sequence[TimeSeries], time_range: TimeRange) -> TimeSeries:
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
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    rrd: RRDSource,
) -> Mapping[RRDMetricRef, TimeSeries]:
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
            consolidation_function=function,
            time_range=time_range,
        )
        for function, rrd_metrics in rrd_metrics_per_function.items()
    }

    result: dict[RRDMetricRef, TimeSeries] = {}
    for metric, (function, rrd_metrics) in rrd_metrics_per_metric.items():
        raw = raw_per_function[function]
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
    services: Iterable[ServiceRef],
    translations: Iterable[translations_v1.Translation],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    rrd: RRDSource,
) -> Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]:
    parsed_translations = parse_translations_from_api(translations)
    performance_data = rrd.fetch_performance_data(list(dict.fromkeys(services)))
    return {
        service: translate_performance_data(perf, parsed_translations, metrics, localizer)
        for service, perf in performance_data.items()
    }


def _metric_data_of(
    graph: Graph,
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> Mapping[RRDMetricRef, RRDMetricData]:
    result: dict[RRDMetricRef, RRDMetricData] = {}
    for metric in graph.rrd_metrics():
        service = ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        if (translated := translated_metrics.get(service, {}).get(metric.metric_name)) is not None:
            result[metric] = translated
    return result


def evaluate_graphs(
    *,
    graphs: Sequence[Graph],
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    rrd: RRDSource,
) -> Sequence[EvaluatedGraph]:
    evaluated = []
    for graph in graphs:
        metric_data = _metric_data_of(graph, translated_metrics)
        evaluated.append(
            evaluate_graph(
                graph,
                metric_data,
                _fetch_series(
                    graph,
                    metric_data,
                    consolidation_function=consolidation_function,
                    time_range=time_range,
                    rrd=rrd,
                ),
                translated_metrics,
                time_range,
            )
        )
    return evaluated


def update_graph_data(
    *,
    graphs: Sequence[Graph],
    translations: Iterable[translations_v1.Translation],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    rrd: RRDSource,
) -> Sequence[EvaluatedGraph]:
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
