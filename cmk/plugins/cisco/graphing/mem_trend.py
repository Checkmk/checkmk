#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_DAY = metrics.Unit(metrics.IECNotation("B/d"))

metric_mem_trend = metrics.Metric(
    name="mem_trend",
    title=Title("Trend of memory usage growth"),
    unit=UNIT_BYTES_PER_DAY,
    color=metrics.Color.BLUE,
)

graph_mem_trend = graphs.Graph(
    name="mem_trend",
    title=Title("Trend of memory usage growth"),
    simple_lines=["mem_trend"],
)
