#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from ._objects import Bidirectional, Graph, MetricName, RRDMetric, RRDMetricData, RRDOriginal
from ._options import CommonOptions, ConsolidationFunction, ServiceRef, TimeRange


@dataclass(frozen=True, kw_only=True)
class TimeSeries:
    time_range: TimeRange
    values: Sequence[float | None]


class FetchRRD(Protocol):
    def translated_metrics(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]: ...

    def time_series(
        self,
        keys: Sequence[RRDOriginal],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDOriginal, TimeSeries]: ...


@dataclass(frozen=True, kw_only=True)
class GraphRequest:
    common: CommonOptions
    graph: Graph | Bidirectional


def _fetch_time_series_per_request(
    request: GraphRequest, rrd: FetchRRD
) -> Mapping[RRDMetric, TimeSeries]:
    # Each metric carries its own consolidation function, so group the sources in a single pass and
    # fetch one batch per distinct function.
    metric_by_source_by_function: dict[ConsolidationFunction, dict[RRDOriginal, RRDMetric]] = {}
    for metric in request.graph.rrd_metrics():
        source = RRDOriginal(metric_name=metric.metric_name, scale=1.0)
        metric_by_source_by_function.setdefault(metric.consolidation_function, {})[source] = metric

    result: dict[RRDMetric, TimeSeries] = {}
    for consolidation_function, metric_by_source in metric_by_source_by_function.items():
        for source, time_series in rrd.time_series(
            list(metric_by_source),
            time_range=request.common.time_range,
            consolidation_function=consolidation_function,
        ).items():
            result[metric_by_source[source]] = time_series
    return result


def fetch_time_series(
    requests: Sequence[GraphRequest],
    *,
    rrd: FetchRRD,
) -> Sequence[Mapping[RRDMetric, TimeSeries]]:
    return [_fetch_time_series_per_request(request, rrd) for request in requests]
