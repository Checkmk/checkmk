#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_if_in_bcast = metrics.Metric(
    name="if_in_bcast",
    title=Title("Input broadcast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_if_in_mcast = metrics.Metric(
    name="if_in_mcast",
    title=Title("Input multicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_if_out_bcast = metrics.Metric(
    name="if_out_bcast",
    title=Title("Output broadcast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_if_out_mcast = metrics.Metric(
    name="if_out_mcast",
    title=Title("Output multicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

graph_bm_packets_bm_packets = graphs.Bidirectional(
    name="bm_packets",
    title=Title("Broadcast/Multicast"),
    lower=graphs.Graph(
        name="bm_packets_out",
        title=Title("Broadcast/Multicast"),
        simple_lines=[
            "if_out_mcast",
            "if_out_bcast",
        ],
    ),
    upper=graphs.Graph(
        name="bm_packets_in",
        title=Title("Broadcast/Multicast"),
        simple_lines=[
            "if_in_mcast",
            "if_in_bcast",
        ],
    ),
)
