#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hop_7_rta = metrics.Metric(
    name="hop_7_rta",
    title=Title("Hop 7 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_7_rtmax = metrics.Metric(
    name="hop_7_rtmax",
    title=Title("Hop 7 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_7_rtmin = metrics.Metric(
    name="hop_7_rtmin",
    title=Title("Hop 7 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_7_rtstddev = metrics.Metric(
    name="hop_7_rtstddev",
    title=Title("Hop 7 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)

graph_hop_7_round_trip_average = graphs.Graph(
    name="hop_7_round_trip_average",
    title=Title("Hop 7 round trip average"),
    simple_lines=[
        "hop_7_rtmax",
        "hop_7_rtmin",
        "hop_7_rta",
        "hop_7_rtstddev",
    ],
)
