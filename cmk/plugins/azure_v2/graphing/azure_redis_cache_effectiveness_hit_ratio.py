#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_azure_redis_cache_hit_ratio = metrics.Metric(
    name="azure_redis_cache_hit_ratio",
    title=Title("Cache hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

perfometer_azure_redis_cache_hit_ratio = perfometers.Perfometer(
    name="azure_redis_cache_hit_ratio",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["azure_redis_cache_hit_ratio"],
)

graph_azure_redis_cache_hit_ratio = graphs.Graph(
    name="azure_redis_cache_hit_ratio",
    title=Title("Hit ratio"),
    compound_lines=["azure_redis_cache_hit_ratio"],
)
