#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_rta = metrics.Metric(
    name="rta",
    title=Title("Round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_rtmax = metrics.Metric(
    name="rtmax",
    title=Title("Round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_rtmin = metrics.Metric(
    name="rtmin",
    title=Title("Round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

perfometer_rta = perfometers.Perfometer(
    name="rta",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["rta"],
)

graph_round_trip_average = graphs.Graph(
    name="round_trip_average",
    title=Title("Round trip average"),
    simple_lines=[
        "rtmax",
        "rtmin",
        "rta",
        metrics.WarningOf("rta"),
        metrics.CriticalOf("rta"),
    ],
)
