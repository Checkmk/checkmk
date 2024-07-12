#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_hop_3_rta = metrics.Metric(
    name="hop_3_rta",
    title=Title("Hop 3 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_3_rtmax = metrics.Metric(
    name="hop_3_rtmax",
    title=Title("Hop 3 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_3_rtmin = metrics.Metric(
    name="hop_3_rtmin",
    title=Title("Hop 3 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_3_rtstddev = metrics.Metric(
    name="hop_3_rtstddev",
    title=Title("Hop 3 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_3_pl = metrics.Metric(
    name="hop_3_pl",
    title=Title("Hop 3 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)

perfometer_hop_3_pl_hop_3_rta = perfometers.Bidirectional(
    name="hop_3_pl_hop_3_rta",
    left=perfometers.Perfometer(
        name="hop_3_pl",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["hop_3_pl"],
    ),
    right=perfometers.Perfometer(
        name="hop_3_rta",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1),
        ),
        segments=["hop_3_rta"],
    ),
)

graph_hop_3_round_trip_average = graphs.Graph(
    name="hop_3_round_trip_average",
    title=Title("Hop 3 round trip average"),
    simple_lines=[
        "hop_3_rtmax",
        "hop_3_rtmin",
        "hop_3_rta",
        "hop_3_rtstddev",
    ],
)

graph_hop_3_packet_loss = graphs.Graph(
    name="hop_3_packet_loss",
    title=Title("Hop 3 packet loss"),
    compound_lines=["hop_3_pl"],
)
