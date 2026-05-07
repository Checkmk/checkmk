#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_idle_servers = metrics.Metric(
    name="idle_servers",
    title=Title("Idle servers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_busy_servers = metrics.Metric(
    name="busy_servers",
    title=Title("Busy servers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

graph_busy_and_idle_servers = graphs.Graph(
    name="busy_and_idle_servers",
    title=Title("Busy and idle servers"),
    compound_lines=[
        "busy_servers",
        "idle_servers",
    ],
)
