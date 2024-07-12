#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_hop_5_rta = metrics.Metric(
    name="hop_5_rta",
    title=Title("Hop 5 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_5_rtmax = metrics.Metric(
    name="hop_5_rtmax",
    title=Title("Hop 5 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_5_rtmin = metrics.Metric(
    name="hop_5_rtmin",
    title=Title("Hop 5 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_5_rtstddev = metrics.Metric(
    name="hop_5_rtstddev",
    title=Title("Hop 5 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_5_pl = metrics.Metric(
    name="hop_5_pl",
    title=Title("Hop 5 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)

perfometer_hop_5_pl_hop_5_rta = perfometers.Bidirectional(
    name="hop_5_pl_hop_5_rta",
    left=perfometers.Perfometer(
        name="hop_5_pl",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["hop_5_pl"],
    ),
    right=perfometers.Perfometer(
        name="hop_5_rta",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1),
        ),
        segments=["hop_5_rta"],
    ),
)

graph_hop_5_round_trip_average = graphs.Graph(
    name="hop_5_round_trip_average",
    title=Title("Hop 5 round trip average"),
    simple_lines=[
        "hop_5_rtmax",
        "hop_5_rtmin",
        "hop_5_rta",
        "hop_5_rtstddev",
    ],
)

graph_hop_5_packet_loss = graphs.Graph(
    name="hop_5_packet_loss",
    title=Title("Hop 5 packet loss"),
    compound_lines=["hop_5_pl"],
)
