#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_active_connections = metrics.Metric(
    name="active_connections",
    title=Title("Active connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)
metric_idle_connections = metrics.Metric(
    name="idle_connections",
    title=Title("Idle connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

perfometer_active_connections = perfometers.Perfometer(
    name="active_connections",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(90)),
    segments=["active_connections"],
)

graph_db_connections = graphs.Graph(
    name="db_connections",
    title=Title("DB Connections"),
    simple_lines=[
        "active_connections",
        "idle_connections",
        metrics.WarningOf("active_connections"),
        metrics.CriticalOf("active_connections"),
    ],
)
