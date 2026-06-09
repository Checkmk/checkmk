#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ._fetch import FetchRRD, RRDSource, TimeSeries
from ._objects import Bidirectional, Graph, RRDMetric
from ._options import CommonOptions, ServiceRef


@dataclass(frozen=True, kw_only=True)
class GraphRequest:
    common: CommonOptions
    service: ServiceRef
    graph: Graph | Bidirectional


def _fetch_time_series_per_request(
    request: GraphRequest, rrd: FetchRRD
) -> Mapping[RRDMetric, TimeSeries]:
    sources = {
        metric: RRDSource(
            service=ServiceRef(
                site_id=request.service.site_id,
                host_name=metric.host_name,
                service_name=metric.service_name,
            ),
            metric_name=metric.metric_name,
            scale=1.0,
        )
        for metric in request.graph.rrd_metrics()
    }
    # Each metric carries its own consolidation function, so the sources are fetched in one batch
    # per distinct function.
    result: dict[RRDMetric, TimeSeries] = {}
    for consolidation_function in {metric.consolidation_function for metric in sources}:
        metric_by_source = {
            source: metric
            for metric, source in sources.items()
            if metric.consolidation_function == consolidation_function
        }
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
