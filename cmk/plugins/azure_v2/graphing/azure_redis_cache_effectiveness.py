#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))

metric_azure_redis_cache_hits = metrics.Metric(
    name="azure_redis_cache_hits",
    title=Title("Cache hits"),
    unit=UNIT_COUNT,
    color=metrics.Color.GREEN,
)

metric_azure_redis_cache_misses = metrics.Metric(
    name="azure_redis_cache_misses",
    title=Title("Cache misses"),
    unit=UNIT_COUNT,
    color=metrics.Color.RED,
)

graph_azure_redis_cache_requests = graphs.Graph(
    name="azure_redis_cache_requests",
    title=Title("Cache requests"),
    simple_lines=["azure_redis_cache_hits", "azure_redis_cache_misses"],
)
