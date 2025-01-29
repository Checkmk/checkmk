#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_connection_time = metrics.Metric(
    name="connection_time",
    title=Title("Connection time"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)

perfometer_connection_time = perfometers.Perfometer(
    name="connection_time",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["connection_time"],
)

graph_time_to_connect = graphs.Graph(
    name="time_to_connect",
    title=Title("Time to connect"),
    compound_lines=["connection_time"],
)
