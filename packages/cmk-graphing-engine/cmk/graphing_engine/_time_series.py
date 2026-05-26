#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ._fetch import FetchRRD, RRDKey, TimeSeries
from ._objects import Bidirectional, Graph, MetricName
from ._options import CommonOptions, ServiceRef


@dataclass(frozen=True, kw_only=True)
class GraphRequest:
    common: CommonOptions
    service: ServiceRef
    graph: Graph | Bidirectional


def _fetch_time_series_per_request(
    request: GraphRequest, rrd: FetchRRD
) -> Mapping[MetricName, TimeSeries]:
    rrd_keys = [
        RRDKey(service=request.service, metric_name=name, scale=1.0)
        for name in request.graph.metric_names()
    ]
    time_series_by_key = rrd.time_series(
        rrd_keys,
        time_range=request.common.time_range,
        consolidation_function=request.common.consolidation_function,
    )
    return {key.metric_name: time_series for key, time_series in time_series_by_key.items()}


def fetch_time_series(
    requests: Sequence[GraphRequest],
    *,
    rrd: FetchRRD,
) -> Sequence[Mapping[MetricName, TimeSeries]]:
    return [_fetch_time_series_per_request(request, rrd) for request in requests]
