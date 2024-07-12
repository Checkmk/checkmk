#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hop_43_pl = metrics.Metric(
    name="hop_43_pl",
    title=Title("Hop 43 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_43_rta = metrics.Metric(
    name="hop_43_rta",
    title=Title("Hop 43 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_43_rtmax = metrics.Metric(
    name="hop_43_rtmax",
    title=Title("Hop 43 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_43_rtmin = metrics.Metric(
    name="hop_43_rtmin",
    title=Title("Hop 43 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_43_rtstddev = metrics.Metric(
    name="hop_43_rtstddev",
    title=Title("Hop 43 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)

perfometer_hop_43_pl_hop_43_rta = perfometers.Bidirectional(
    name="hop_43_pl_hop_43_rta",
    left=perfometers.Perfometer(
        name="hop_43_pl",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["hop_43_pl"],
    ),
    right=perfometers.Perfometer(
        name="hop_43_rta",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1),
        ),
        segments=["hop_43_rta"],
    ),
)

graph_hop_43_round_trip_average = graphs.Graph(
    name="hop_43_round_trip_average",
    title=Title("Hop 43 round trip average"),
    simple_lines=[
        "hop_43_rtmax",
        "hop_43_rtmin",
        "hop_43_rta",
        "hop_43_rtstddev",
    ],
)

graph_hop_43_packet_loss = graphs.Graph(
    name="hop_43_packet_loss",
    title=Title("Hop 43 packet loss"),
    compound_lines=["hop_43_pl"],
)
