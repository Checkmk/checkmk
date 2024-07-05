#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_running_sessions = metrics.Metric(
    name="running_sessions",
    title=Title("Running sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_total_sessions = metrics.Metric(
    name="total_sessions",
    title=Title("Total sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

perfometer_running_sessions = perfometers.Perfometer(
    name="running_sessions",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed("total_sessions"),
    ),
    segments=["running_sessions"],
)
perfometer_running_sessions = perfometers.Perfometer(
    name="running_sessions",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20),
    ),
    segments=["running_sessions"],
)

graph_number_of_total_and_running_sessions = graphs.Graph(
    name="number_of_total_and_running_sessions",
    title=Title("Number of total and running sessions"),
    simple_lines=[
        "running_sessions",
        "total_sessions",
    ],
)
