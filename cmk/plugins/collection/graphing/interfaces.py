#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BITS_PER_SECOND = metrics.Unit(metrics.IECNotation("bits/s"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_if_in_bcast = metrics.Metric(
    name="if_in_bcast",
    title=Title("Input broadcast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_if_in_bps = metrics.Metric(
    name="if_in_bps",
    title=Title("Input bandwidth"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_if_in_discards = metrics.Metric(
    name="if_in_discards",
    title=Title("Input discards"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_if_in_errors = metrics.Metric(
    name="if_in_errors",
    title=Title("Input errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_if_in_mcast = metrics.Metric(
    name="if_in_mcast",
    title=Title("Input multicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_if_in_non_unicast = metrics.Metric(
    name="if_in_non_unicast",
    title=Title("Input non-unicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_if_in_octets = metrics.Metric(
    name="if_in_octets",
    title=Title("Input octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)
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
metric_if_out_bcast = metrics.Metric(
    name="if_out_bcast",
    title=Title("Output broadcast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_if_out_bps = metrics.Metric(
    name="if_out_bps",
    title=Title("Output bandwidth"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_if_out_discards = metrics.Metric(
    name="if_out_discards",
    title=Title("Output discards"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_if_out_errors = metrics.Metric(
    name="if_out_errors",
    title=Title("Output errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_if_out_mcast = metrics.Metric(
    name="if_out_mcast",
    title=Title("Output multicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_if_out_non_unicast = metrics.Metric(
    name="if_out_non_unicast",
    title=Title("Output non-unicast packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_if_out_non_unicast_octets = metrics.Metric(
    name="if_out_non_unicast_octets",
    title=Title("Output non-unicast octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_if_out_octets = metrics.Metric(
    name="if_out_octets",
    title=Title("Output octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
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
metric_if_out_unicast_octets = metrics.Metric(
    name="if_out_unicast_octets",
    title=Title("Output unicast octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_if_total_bps = metrics.Metric(
    name="if_total_bps",
    title=Title("Total bandwidth (sum of in and out)"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.GREEN,
)

perfometer_if_octets = perfometers.Bidirectional(
    name="if_octets",
    left=perfometers.Perfometer(
        name="if_in_octets",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(500000),
        ),
        segments=["if_in_octets"],
    ),
    right=perfometers.Perfometer(
        name="if_out_octets",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(500000),
        ),
        segments=["if_out_octets"],
    ),
)
perfometer_if_unicast_octets = perfometers.Bidirectional(
    name="if_unicast_octets",
    left=perfometers.Perfometer(
        name="if_unicast_octets_out",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(500000),
        ),
        segments=[
            metrics.Sum(
                Title(""),
                metrics.Color.GRAY,
                [
                    "if_out_unicast_octets",
                    "if_out_non_unicast_octets",
                ],
            )
        ],
    ),
    right=perfometers.Perfometer(
        name="if_in_octets",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(500000),
        ),
        segments=["if_in_octets"],
    ),
)
perfometer_if_bps = perfometers.Bidirectional(
    name="if_bps",
    left=perfometers.Perfometer(
        name="if_in_bps",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(500000),
        ),
        segments=["if_in_bps"],
    ),
    right=perfometers.Perfometer(
        name="if_out_bps",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(500000),
        ),
        segments=["if_out_bps"],
    ),
)

graph_bandwidth_translated = graphs.Bidirectional(
    name="bandwidth_translated",
    title=Title("Bandwidth"),
    lower=graphs.Graph(
        name="bandwidth_translated_out",
        title=Title("Bandwidth"),
        compound_lines=[
            metrics.Product(
                Title("Output bandwidth"),
                UNIT_BITS_PER_SECOND,
                metrics.Color.GRAY,
                [
                    "if_out_octets",
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.BLUE,
                        8.0,
                    ),
                ],
            )
        ],
        simple_lines=[
            metrics.WarningOf("if_out_octets"),
            metrics.CriticalOf("if_out_octets"),
        ],
    ),
    upper=graphs.Graph(
        name="bandwidth_translated_in",
        title=Title("Bandwidth"),
        compound_lines=[
            metrics.Product(
                Title("Input bandwidth"),
                UNIT_BITS_PER_SECOND,
                metrics.Color.GRAY,
                [
                    "if_in_octets",
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.BLUE,
                        8.0,
                    ),
                ],
            )
        ],
        simple_lines=[
            metrics.WarningOf("if_in_octets"),
            metrics.CriticalOf("if_in_octets"),
        ],
    ),
)
graph_traffic = graphs.Bidirectional(
    name="traffic",
    title=Title("Traffic"),
    lower=graphs.Graph(
        name="traffic_out",
        title=Title("Traffic"),
        compound_lines=[
            "if_out_non_unicast_octets",
            "if_out_unicast_octets",
        ],
    ),
    upper=graphs.Graph(
        name="traffic_in",
        title=Title("Traffic"),
        compound_lines=["if_in_octets"],
    ),
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
graph_if_errors_if_errors = graphs.Bidirectional(
    name="if_errors",
    title=Title("Errors"),
    lower=graphs.Graph(
        name="if_errors_out",
        title=Title("Errors"),
        compound_lines=[
            "if_out_errors",
            "if_out_discards",
        ],
    ),
    upper=graphs.Graph(
        name="if_errors_in",
        title=Title("Errors"),
        compound_lines=[
            "if_in_errors",
            "if_in_discards",
        ],
    ),
)
graph_packets_1_packets_1 = graphs.Bidirectional(
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
graph_packets_3_packets_3 = graphs.Bidirectional(
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
graph_packets_2_packets_2 = graphs.Bidirectional(
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
graph_bandwidth_bandwidth = graphs.Bidirectional(
    name="bandwidth",
    title=Title("Bandwidth"),
    lower=graphs.Graph(
        name="bandwidth_out",
        title=Title("Bandwidth"),
        compound_lines=["if_out_bps"],
        simple_lines=[
            metrics.WarningOf("if_out_bps"),
            metrics.CriticalOf("if_out_bps"),
        ],
    ),
    upper=graphs.Graph(
        name="bandwidth_in",
        title=Title("Bandwidth"),
        compound_lines=["if_in_bps"],
        simple_lines=[
            metrics.WarningOf("if_in_bps"),
            metrics.CriticalOf("if_in_bps"),
        ],
    ),
)
