#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BITS_PER_SECOND = metrics.Unit(metrics.IECNotation("bits/s"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_if_in_octets = metrics.Metric(
    name="if_in_octets",
    title=Title("Input octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_if_out_octets = metrics.Metric(
    name="if_out_octets",
    title=Title("Output octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_if_out_unicast_octets = metrics.Metric(
    name="if_out_unicast_octets",
    title=Title("Output unicast octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_if_out_non_unicast_octets = metrics.Metric(
    name="if_out_non_unicast_octets",
    title=Title("Output non-unicast octets"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)

perfometer_if_octets = perfometers.Bidirectional(
    name="if_octets",
    left=perfometers.Perfometer(
        name="if_in_octets",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(125_000_000),
        ),
        segments=["if_in_octets"],
    ),
    right=perfometers.Perfometer(
        name="if_out_octets",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(125_000_000),
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
            perfometers.Open(125_000_000),
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
            perfometers.Open(125_000_000),
        ),
        segments=["if_in_octets"],
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
                metrics.Color.BLUE,
                [
                    "if_out_octets",
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        8.0,
                    ),
                ],
            )
        ],
        simple_lines=[
            metrics.Product(
                Title("Warning of Output bandwidth"),
                UNIT_BITS_PER_SECOND,
                metrics.Color.YELLOW,
                [
                    metrics.WarningOf("if_out_octets"),
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        8.0,
                    ),
                ],
            ),
            metrics.Product(
                Title("Critical of Output bandwidth"),
                UNIT_BITS_PER_SECOND,
                metrics.Color.RED,
                [
                    metrics.CriticalOf("if_out_octets"),
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        8.0,
                    ),
                ],
            ),
        ],
    ),
    upper=graphs.Graph(
        name="bandwidth_translated_in",
        title=Title("Bandwidth"),
        compound_lines=[
            metrics.Product(
                Title("Input bandwidth"),
                UNIT_BITS_PER_SECOND,
                metrics.Color.GREEN,
                [
                    "if_in_octets",
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        8.0,
                    ),
                ],
            )
        ],
        simple_lines=[
            metrics.Product(
                Title("Warning of Input bandwidth"),
                UNIT_BITS_PER_SECOND,
                metrics.Color.YELLOW,
                [
                    metrics.WarningOf("if_in_octets"),
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        8.0,
                    ),
                ],
            ),
            metrics.Product(
                Title("Critical of Input bandwidth"),
                UNIT_BITS_PER_SECOND,
                metrics.Color.RED,
                [
                    metrics.CriticalOf("if_in_octets"),
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        8.0,
                    ),
                ],
            ),
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
