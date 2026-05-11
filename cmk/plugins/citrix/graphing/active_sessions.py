#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_active_sessions = metrics.Metric(
    name="active_sessions",
    title=Title("Active sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_active_sessions_peak = metrics.Metric(
    name="active_sessions_peak",
    title=Title("Peak value of active sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_active_sessions = perfometers.Perfometer(
    name="active_sessions",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(90),
    ),
    segments=["active_sessions"],
)

graph_active_sessions_with_peak_value = graphs.Graph(
    name="active_sessions_with_peak_value",
    title=Title("Active sessions"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf(
            "active_sessions_peak",
            metrics.Color.GRAY,
        ),
    ),
    compound_lines=["active_sessions"],
    simple_lines=[
        "active_sessions_peak",
        metrics.WarningOf("active_sessions"),
        metrics.CriticalOf("active_sessions"),
    ],
)
