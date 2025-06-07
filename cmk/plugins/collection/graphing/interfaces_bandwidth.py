#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BITS_PER_SECOND = metrics.Unit(metrics.SINotation("bits/s"))


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
