#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_util_50 = metrics.Metric(
    name="util_50",
    title=Title("CPU utilization (50th percentile)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_util_95 = metrics.Metric(
    name="util_95",
    title=Title("CPU utilization (95th percentile)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_util_99 = metrics.Metric(
    name="util_99",
    title=Title("CPU utilization (99th percentile)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

graph_cpu_utilization_percentile = graphs.Graph(
    name="cpu_utilization_percentile",
    title=Title("CPU utilization"),
    simple_lines=[
        "util_50",
        "util_95",
        "util_99",
    ],
)
