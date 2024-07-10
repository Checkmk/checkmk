#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hop_13_rta = metrics.Metric(
    name="hop_13_rta",
    title=Title("Hop 13 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_13_rtmax = metrics.Metric(
    name="hop_13_rtmax",
    title=Title("Hop 13 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_13_rtmin = metrics.Metric(
    name="hop_13_rtmin",
    title=Title("Hop 13 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_13_rtstddev = metrics.Metric(
    name="hop_13_rtstddev",
    title=Title("Hop 13 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)

graph_hop_13_round_trip_average = graphs.Graph(
    name="hop_13_round_trip_average",
    title=Title("Hop 13 round trip average"),
    simple_lines=[
        "hop_13_rtmax",
        "hop_13_rtmin",
        "hop_13_rta",
        "hop_13_rtstddev",
    ],
)
