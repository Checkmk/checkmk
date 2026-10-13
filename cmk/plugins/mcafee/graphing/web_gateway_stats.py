#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_connections_blocked_rate = metrics.Metric(
    name="connections_blocked_rate",
    title=Title("Blocked connections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_infections_rate = metrics.Metric(
    name="infections_rate",
    title=Title("Infections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

graph_web_gateway_statistics = graphs.Graph(
    name="web_gateway_statistics",
    title=Title("Web gateway statistics"),
    compound_lines=[
        "infections_rate",
        "connections_blocked_rate",
    ],
)
