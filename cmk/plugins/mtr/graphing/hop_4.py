#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_hop_4_rta = metrics.Metric(
    name="hop_4_rta",
    title=Title("Hop 4 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_4_rtmax = metrics.Metric(
    name="hop_4_rtmax",
    title=Title("Hop 4 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_4_rtmin = metrics.Metric(
    name="hop_4_rtmin",
    title=Title("Hop 4 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_4_rtstddev = metrics.Metric(
    name="hop_4_rtstddev",
    title=Title("Hop 4 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_4_pl = metrics.Metric(
    name="hop_4_pl",
    title=Title("Hop 4 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)

perfometer_hop_4_pl_hop_4_rta = perfometers.Bidirectional(
    name="hop_4_pl_hop_4_rta",
    left=perfometers.Perfometer(
        name="hop_4_pl",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["hop_4_pl"],
    ),
    right=perfometers.Perfometer(
        name="hop_4_rta",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1),
        ),
        segments=["hop_4_rta"],
    ),
)

graph_hop_4_round_trip_average = graphs.Graph(
    name="hop_4_round_trip_average",
    title=Title("Hop 4 round trip average"),
    simple_lines=[
        "hop_4_rtmax",
        "hop_4_rtmin",
        "hop_4_rta",
        "hop_4_rtstddev",
    ],
)

graph_hop_4_packet_loss = graphs.Graph(
    name="hop_4_packet_loss",
    title=Title("Hop 4 packet loss"),
    compound_lines=["hop_4_pl"],
)
