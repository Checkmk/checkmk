#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_edge_tcp_packets_dropped = metrics.Metric(
    name="edge_tcp_packets_dropped",
    title=Title("A/V Edge - TCP packets dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_edge_udp_packets_dropped = metrics.Metric(
    name="edge_udp_packets_dropped",
    title=Title("A/V Edge - UDP packets dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_packets_dropped = graphs.Graph(
    name="packets_dropped",
    title=Title("Packets dropped"),
    simple_lines=[
        "edge_udp_packets_dropped",
        "edge_tcp_packets_dropped",
    ],
)
