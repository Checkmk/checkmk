#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BITS_PER_SECOND = metrics.Unit(metrics.IECNotation("bits/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))


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
            metrics.WarningOf("if_in_octets"),
            metrics.CriticalOf("if_in_octets"),
        ],
    ),
)
