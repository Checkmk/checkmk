#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_active_modems = metrics.Metric(
    name="active_modems",
    title=Title("Active modems"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_registered_modems = metrics.Metric(
    name="registered_modems",
    title=Title("Registered modems"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_total_modems = metrics.Metric(
    name="total_modems",
    title=Title("Total number of modems"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_modems = graphs.Graph(
    name="modems",
    title=Title("Modems"),
    compound_lines=["active_modems"],
    simple_lines=[
        "registered_modems",
        "total_modems",
    ],
)
