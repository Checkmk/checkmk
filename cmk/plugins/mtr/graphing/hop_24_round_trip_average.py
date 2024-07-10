#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hop_24_rta = metrics.Metric(
    name="hop_24_rta",
    title=Title("Hop 24 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_24_rtmax = metrics.Metric(
    name="hop_24_rtmax",
    title=Title("Hop 24 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_24_rtmin = metrics.Metric(
    name="hop_24_rtmin",
    title=Title("Hop 24 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_24_rtstddev = metrics.Metric(
    name="hop_24_rtstddev",
    title=Title("Hop 24 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)

graph_hop_24_round_trip_average = graphs.Graph(
    name="hop_24_round_trip_average",
    title=Title("Hop 24 round trip average"),
    simple_lines=[
        "hop_24_rtmax",
        "hop_24_rtmin",
        "hop_24_rta",
        "hop_24_rtstddev",
    ],
)
