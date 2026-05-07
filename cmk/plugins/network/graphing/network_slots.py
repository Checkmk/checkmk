#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_open_slots = metrics.Metric(
    name="open_slots",
    title=Title("Open slots"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)
metric_total_slots = metrics.Metric(
    name="total_slots",
    title=Title("Total slots"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

graph_total_and_open_slots = graphs.Graph(
    name="total_and_open_slots",
    title=Title("Total and open slots"),
    compound_lines=["total_slots"],
    simple_lines=["open_slots"],
)
