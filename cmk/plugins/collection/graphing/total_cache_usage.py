#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_total_cache_usage = metrics.Metric(
    name="total_cache_usage",
    title=Title("Total cache usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_total_cache_usage = perfometers.Perfometer(
    name="total_cache_usage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["total_cache_usage"],
)

graph_total_cache_usage = graphs.Graph(
    name="total_cache_usage",
    title=Title("Total cache usage"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["total_cache_usage"],
)
