#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_cache_hit_ratio = metrics.Metric(
    name="cache_hit_ratio",
    title=Title("Cache hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_prefetch_data_hit_ratio = metrics.Metric(
    name="prefetch_data_hit_ratio",
    title=Title("Prefetch data hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_prefetch_metadata_hit_ratio = metrics.Metric(
    name="prefetch_metadata_hit_ratio",
    title=Title("Prefetch metadata hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

perfometer_cache_hit_ratio = perfometers.Perfometer(
    name="cache_hit_ratio",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["cache_hit_ratio"],
)

graph_cache_hit_ratio = graphs.Graph(
    name="cache_hit_ratio",
    title=Title("Cache hit ratio"),
    simple_lines=[
        "cache_hit_ratio",
        "prefetch_metadata_hit_ratio",
        "prefetch_data_hit_ratio",
    ],
)
