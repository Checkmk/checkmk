#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_max_user = metrics.Metric(
    name="max_user",
    title=Title("Maximum allowed users"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_num_user = metrics.Metric(
    name="num_user",
    title=Title("User"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

perfometer_num_user = perfometers.Perfometer(
    name="num_user",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed("max_user"),
    ),
    segments=["num_user"],
)

graph_firewall_users = graphs.Graph(
    name="firewall_users",
    title=Title("Number of active users"),
    simple_lines=[
        "num_user",
        "max_user",
    ],
)
