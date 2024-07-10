#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_pages_bw = metrics.Metric(
    name="pages_bw",
    title=Title("B/W"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)
metric_pages_bw_a3 = metrics.Metric(
    name="pages_bw_a3",
    title=Title("B/W A3"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pages_bw_a4 = metrics.Metric(
    name="pages_bw_a4",
    title=Title("B/W A4"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pages_color = metrics.Metric(
    name="pages_color",
    title=Title("Color"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_pages_color_a3 = metrics.Metric(
    name="pages_color_a3",
    title=Title("Color A3"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_pages_color_a4 = metrics.Metric(
    name="pages_color_a4",
    title=Title("Color A4"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_pages_total = metrics.Metric(
    name="pages_total",
    title=Title("Total printed pages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

perfometer_pages_total = perfometers.Perfometer(
    name="pages_total",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(200000)),
    segments=["pages_total"],
)

graph_printed_pages = graphs.Graph(
    name="printed_pages",
    title=Title("Printed pages"),
    minimal_range=graphs.MinimalRange(0, metrics.MaximumOf("pages_total", metrics.Color.GRAY)),
    compound_lines=[
        "pages_color_a4",
        "pages_color_a3",
        "pages_bw_a4",
        "pages_bw_a3",
        "pages_color",
        "pages_bw",
    ],
    simple_lines=["pages_total"],
    optional=[
        "pages_color_a4",
        "pages_color_a3",
        "pages_bw_a4",
        "pages_bw_a3",
        "pages_color",
        "pages_bw",
    ],
)
