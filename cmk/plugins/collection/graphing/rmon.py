#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_broadcast_packets = metrics.Metric(
    name="broadcast_packets",
    title=Title("Broadcast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_multicast_packets = metrics.Metric(
    name="multicast_packets",
    title=Title("Multicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_rmon_packets_1023 = metrics.Metric(
    name="rmon_packets_1023",
    title=Title("Packets of size 512-1023 bytes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_rmon_packets_127 = metrics.Metric(
    name="rmon_packets_127",
    title=Title("Packets of size 64-127 bytes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_rmon_packets_1518 = metrics.Metric(
    name="rmon_packets_1518",
    title=Title("Packets of size 1024-1518 bytes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_rmon_packets_255 = metrics.Metric(
    name="rmon_packets_255",
    title=Title("Packets of size 128-255 bytes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_rmon_packets_511 = metrics.Metric(
    name="rmon_packets_511",
    title=Title("Packets of size 256-511 bytes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_rmon_packets_63 = metrics.Metric(
    name="rmon_packets_63",
    title=Title("Packets of size 0-63 bytes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GRAY,
)

graph_rmon_packets_per_second = graphs.Graph(
    name="rmon_packets_per_second",
    title=Title("RMON packets per second"),
    compound_lines=[
        "broadcast_packets",
        "multicast_packets",
        "rmon_packets_63",
        "rmon_packets_127",
        "rmon_packets_255",
        "rmon_packets_511",
        "rmon_packets_1023",
        "rmon_packets_1518",
    ],
)
