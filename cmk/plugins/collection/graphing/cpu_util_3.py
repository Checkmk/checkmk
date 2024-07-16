#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_util1 = metrics.Metric(
    name="util1",
    title=Title("CPU utilization last minute"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_util15 = metrics.Metric(
    name="util15",
    title=Title("CPU utilization last 15 minutes"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)

perfometer_util1 = perfometers.Perfometer(
    name="util1",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["util1"],
)

graph_util_average_2 = graphs.Graph(
    name="util_average_2",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["util1"],
    simple_lines=[
        "util15",
        metrics.WarningOf("util1"),
        metrics.CriticalOf("util1"),
    ],
)
