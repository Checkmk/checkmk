#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_tapes_free = metrics.Metric(
    name="tapes_free",
    title=Title("Free tapes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_tapes_total = metrics.Metric(
    name="tapes_total",
    title=Title("Total number of tapes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_tapes_utilization = graphs.Graph(
    name="tapes_utilization",
    title=Title("Tapes utilization"),
    compound_lines=["tapes_free"],
    simple_lines=[
        "tapes_total",
        metrics.WarningOf("tapes_free"),
        metrics.CriticalOf("tapes_free"),
    ],
)
