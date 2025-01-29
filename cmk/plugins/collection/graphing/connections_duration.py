#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_connections_duration_max = metrics.Metric(
    name="connections_duration_max",
    title=Title("Connections duration max"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_connections_duration_mean = metrics.Metric(
    name="connections_duration_mean",
    title=Title("Connections duration mean"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_connections_duration_min = metrics.Metric(
    name="connections_duration_min",
    title=Title("Connections duration min"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

graph_connection_durations = graphs.Graph(
    name="connection_durations",
    title=Title("Connection durations"),
    simple_lines=[
        "connections_duration_min",
        "connections_duration_max",
        "connections_duration_mean",
    ],
)
