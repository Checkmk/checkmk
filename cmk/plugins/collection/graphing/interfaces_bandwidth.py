#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BITS_PER_SECOND = metrics.Unit(metrics.SINotation("bits/s"))

metric_if_in_bps = metrics.Metric(
    name="if_in_bps",
    title=Title("Input bandwidth"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_if_out_bps = metrics.Metric(
    name="if_out_bps",
    title=Title("Output bandwidth"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_if_bps = perfometers.Bidirectional(
    name="if_bps",
    left=perfometers.Perfometer(
        name="if_in_bps",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1_000_000_000),
        ),
        segments=["if_in_bps"],
    ),
    right=perfometers.Perfometer(
        name="if_out_bps",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1_000_000_000),
        ),
        segments=["if_out_bps"],
    ),
)

graph_bandwidth = graphs.Bidirectional(
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
