#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hop_39_rta = metrics.Metric(
    name="hop_39_rta",
    title=Title("Hop 39 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_39_rtmax = metrics.Metric(
    name="hop_39_rtmax",
    title=Title("Hop 39 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_39_rtmin = metrics.Metric(
    name="hop_39_rtmin",
    title=Title("Hop 39 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_39_rtstddev = metrics.Metric(
    name="hop_39_rtstddev",
    title=Title("Hop 39 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)

graph_hop_39_round_trip_average = graphs.Graph(
    name="hop_39_round_trip_average",
    title=Title("Hop 39 round trip average"),
    simple_lines=[
        "hop_39_rtmax",
        "hop_39_rtmin",
        "hop_39_rta",
        "hop_39_rtstddev",
    ],
)
