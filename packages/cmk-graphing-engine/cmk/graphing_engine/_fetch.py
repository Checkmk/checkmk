#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from ._objects import (
    Graph,
    PerformanceDataByService,
    RRDMetric,
    RRDMetricRef,
    RRDMetricWithCF,
    ServiceRef,
)
from ._options import ConsolidationFunction, TimeRange


@dataclass(frozen=True, kw_only=True)
class TimeSeries:
    time_range: TimeRange
    values: Sequence[float | None]


class FetchRRD(Protocol):
    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> PerformanceDataByService: ...

    def time_series(
        self,
        rrd_metrics: Sequence[RRDMetricRef],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetricRef, TimeSeries]: ...


@dataclass(frozen=True, kw_only=True)
class GraphRequest:
    time_range: TimeRange
    consolidation_function: ConsolidationFunction
    graph: Graph


def _consolidation_function(metric: RRDMetricRef, request: GraphRequest) -> ConsolidationFunction:
    match metric:
        case RRDMetricWithCF():
            return metric.consolidation_function
        case RRDMetric():
            return request.consolidation_function


def _fetch_time_series_per_request(
    request: GraphRequest, rrd: FetchRRD
) -> Mapping[RRDMetricRef, TimeSeries]:
    # A pinned metric is fetched with its own consolidation function, a bare one with the request's.
    # Group the metrics in a single pass and fetch one batch per distinct function.
    metrics_by_function: dict[ConsolidationFunction, list[RRDMetricRef]] = {}
    for metric in request.graph.rrd_metrics():
        metrics_by_function.setdefault(_consolidation_function(metric, request), []).append(metric)

    result: dict[RRDMetricRef, TimeSeries] = {}
    for consolidation_function, metrics in metrics_by_function.items():
        result.update(
            rrd.time_series(
                metrics,
                time_range=request.time_range,
                consolidation_function=consolidation_function,
            )
        )
    return result


def fetch_time_series(
    requests: Sequence[GraphRequest],
    *,
    rrd: FetchRRD,
) -> Sequence[Mapping[RRDMetricRef, TimeSeries]]:
    return [_fetch_time_series_per_request(request, rrd) for request in requests]
