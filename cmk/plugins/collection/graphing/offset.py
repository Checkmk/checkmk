#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_jitter = metrics.Metric(
    name="jitter",
    title=Title("Time dispersion (jitter)"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_time_offset = metrics.Metric(
    name="time_offset",
    title=Title("Time offset"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)

perfometer_time_offset = perfometers.Perfometer(
    name="time_offset",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["time_offset"],
)

graph_time_offset = graphs.Graph(
    name="time_offset",
    title=Title("Time offset"),
    minimal_range=graphs.MinimalRange(
        0.0,
        metrics.CriticalOf("time_offset"),
    ),
    compound_lines=["time_offset"],
    simple_lines=[
        "jitter",
        metrics.CriticalOf("time_offset"),
        metrics.WarningOf("time_offset"),
    ],
    optional=["jitter"],
)
