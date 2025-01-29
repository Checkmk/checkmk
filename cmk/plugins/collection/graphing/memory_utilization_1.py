#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_memory_util_50 = metrics.Metric(
    name="memory_util_50",
    title=Title("Memory utilization (50th percentile)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_memory_util_95 = metrics.Metric(
    name="memory_util_95",
    title=Title("Memory utilization (95th percentile)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_memory_util_99 = metrics.Metric(
    name="memory_util_99",
    title=Title("Memory utilization (99th percentile)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

graph_memory_utilization_percentile = graphs.Graph(
    name="memory_utilization_percentile",
    title=Title("Memory utilization"),
    simple_lines=[
        "memory_util_50",
        "memory_util_95",
        "memory_util_99",
    ],
)
