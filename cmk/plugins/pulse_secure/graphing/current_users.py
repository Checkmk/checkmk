#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_current_users = metrics.Metric(
    name="current_users",
    title=Title("Current users"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_current_users = graphs.Graph(
    name="current_users",
    title=Title("Number of signed-in users"),
    compound_lines=["current_users"],
    simple_lines=[
        metrics.WarningOf("current_users"),
        metrics.CriticalOf("current_users"),
    ],
)
