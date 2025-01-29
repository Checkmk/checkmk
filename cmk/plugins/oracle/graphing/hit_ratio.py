#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_oracle_library_cache_hit_ratio = metrics.Metric(
    name="oracle_library_cache_hit_ratio",
    title=Title("Oracle library cache hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_oracle_buffer_hit_ratio = metrics.Metric(
    name="oracle_buffer_hit_ratio",
    title=Title("Oracle buffer hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

perfometer_oracle_hit_ratio = perfometers.Stacked(
    name="oracle_hit_ratio",
    lower=perfometers.Perfometer(
        name="oracle_library_cache_hit_ratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["oracle_library_cache_hit_ratio"],
    ),
    upper=perfometers.Perfometer(
        name="oracle_buffer_hit_ratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["oracle_buffer_hit_ratio"],
    ),
)

graph_oracle_hit_ratio = graphs.Bidirectional(
    name="oracle_hit_ratio",
    title=Title("Oracle hit ratio"),
    lower=graphs.Graph(
        name="oracle_hit_ratio",
        title=Title("Oracle library cache hit ratio"),
        compound_lines=["oracle_library_cache_hit_ratio"],
    ),
    upper=graphs.Graph(
        name="oracle_hit_ratio",
        title=Title("Oracle buffer hit ratio"),
        compound_lines=["oracle_buffer_hit_ratio"],
    ),
)
