#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_if_in_pkts = metrics.Metric(
    name="if_in_pkts",
    title=Title("Input packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_if_in_unicast = metrics.Metric(
    name="if_in_unicast",
    title=Title("Input unicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_if_in_non_unicast = metrics.Metric(
    name="if_in_non_unicast",
    title=Title("Input non-unicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_if_out_pkts = metrics.Metric(
    name="if_out_pkts",
    title=Title("Output packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_if_out_unicast = metrics.Metric(
    name="if_out_unicast",
    title=Title("Output unicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_if_out_non_unicast = metrics.Metric(
    name="if_out_non_unicast",
    title=Title("Output non-unicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_packets_1 = graphs.Bidirectional(
    name="packets_1",
    title=Title("Packets"),
    lower=graphs.Graph(
        name="packets_1_out",
        title=Title("Packets"),
        simple_lines=[
            "if_out_unicast",
            "if_out_non_unicast",
        ],
    ),
    upper=graphs.Graph(
        name="packets_1_in",
        title=Title("Packets"),
        simple_lines=[
            "if_in_unicast",
            "if_in_non_unicast",
        ],
    ),
)
graph_packets_2 = graphs.Bidirectional(
    name="packets_2",
    title=Title("Packets"),
    lower=graphs.Graph(
        name="packets_2_out",
        title=Title("Packets"),
        compound_lines=[
            "if_out_non_unicast",
            "if_out_unicast",
        ],
    ),
    upper=graphs.Graph(
        name="packets_2_in",
        title=Title("Packets"),
        compound_lines=["if_in_pkts"],
    ),
)
graph_packets_3 = graphs.Bidirectional(
    name="packets_3",
    title=Title("Packets"),
    lower=graphs.Graph(
        name="packets_3_out",
        title=Title("Packets"),
        compound_lines=["if_out_pkts"],
    ),
    upper=graphs.Graph(
        name="packets_3_in",
        title=Title("Packets"),
        compound_lines=["if_in_pkts"],
    ),
)
