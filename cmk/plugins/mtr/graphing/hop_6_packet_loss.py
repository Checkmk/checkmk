#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_hop_6_pl = metrics.Metric(
    name="hop_6_pl",
    title=Title("Hop 6 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)

graph_hop_6_packet_loss = graphs.Graph(
    name="hop_6_packet_loss",
    title=Title("Hop 6 packet loss"),
    compound_lines=["hop_6_pl"],
)
