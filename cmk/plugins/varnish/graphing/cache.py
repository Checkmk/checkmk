#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_cache_hit_rate = metrics.Metric(
    name="varnish_cache_hit_rate",
    title=Title("Cache hits"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_cache_hitpass_rate = metrics.Metric(
    name="varnish_cache_hitpass_rate",
    title=Title("Cache hits for pass"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_cache_miss_rate = metrics.Metric(
    name="varnish_cache_miss_rate",
    title=Title("Cache misses"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_varnish_cache = graphs.Graph(
    name="varnish_cache",
    title=Title("Varnish Cache"),
    simple_lines=[
        "varnish_cache_miss_rate",
        "varnish_cache_hit_rate",
        "varnish_cache_hitpass_rate",
    ],
)
