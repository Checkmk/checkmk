#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_printer_queue = metrics.Metric(
    name="printer_queue",
    title=Title("Printer queue length"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

perfometer_printer_queue = perfometers.Perfometer(
    name="printer_queue",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(20)),
    segments=["printer_queue"],
)

graph_printer_queue = graphs.Graph(
    name="printer_queue",
    title=Title("Printer queue length"),
    minimal_range=graphs.MinimalRange(0, 10),
    compound_lines=["printer_queue"],
)
