#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
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
metric_printer_queue = metrics.Metric(
    name="printer_queue",
    title=Title("Printer queue length"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_supply_toner_magenta = metrics.Metric(
    name="supply_toner_magenta",
    title=Title("Supply toner magenta"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_supply_toner_cyan = metrics.Metric(
    name="supply_toner_cyan",
    title=Title("Supply toner cyan"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_supply_toner_other = metrics.Metric(
    name="supply_toner_other",
    title=Title("Supply toner"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_supply_toner_yellow = metrics.Metric(
    name="supply_toner_yellow",
    title=Title("Supply toner yellow"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_supply_toner_black = metrics.Metric(
    name="supply_toner_black",
    title=Title("Supply toner black"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_pages_a4 = metrics.Metric(
    name="pages_a4",
    title=Title("A4"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pages_a3 = metrics.Metric(
    name="pages_a3",
    title=Title("A3"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_CYAN,
)

perfometer_pages = perfometers.Perfometer(
    name="pages",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000)),
    segments=["pages"],
)
perfometer_pages_total = perfometers.Perfometer(
    name="pages_total",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(200000)),
    segments=["pages_total"],
)
perfometer_printer_queue = perfometers.Perfometer(
    name="printer_queue",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(20)),
    segments=["printer_queue"],
)
perfometer_supply_toner_black = perfometers.Perfometer(
    name="supply_toner_black",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["supply_toner_black"],
)
perfometer_supply_toner_magenta = perfometers.Perfometer(
    name="supply_toner_magenta",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["supply_toner_magenta"],
)
perfometer_supply_toner_cyan = perfometers.Perfometer(
    name="supply_toner_cyan",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["supply_toner_cyan"],
)
perfometer_supply_toner_other = perfometers.Perfometer(
    name="supply_toner_other",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["supply_toner_other"],
)
perfometer_supply_toner_yellow = perfometers.Perfometer(
    name="supply_toner_yellow",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["supply_toner_yellow"],
)
perfometer_supply_toner_black = perfometers.Perfometer(
    name="supply_toner_black",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["supply_toner_black"],
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
graph_printer_queue = graphs.Graph(
    name="printer_queue",
    title=Title("Printer queue length"),
    minimal_range=graphs.MinimalRange(0, 10),
    compound_lines=["printer_queue"],
)
graph_supply_toner_magenta = graphs.Graph(
    name="supply_toner_magenta",
    title=Title("Supply toner magenta"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=["supply_toner_magenta"],
)
graph_supply_toner_cyan = graphs.Graph(
    name="supply_toner_cyan",
    title=Title("Supply toner cyan"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=["supply_toner_cyan"],
)
graph_supply_toner_other = graphs.Graph(
    name="supply_toner_other",
    title=Title("Supply toner"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=["supply_toner_other"],
)
graph_supply_toner_yellow = graphs.Graph(
    name="supply_toner_yellow",
    title=Title("Supply toner yellow"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=["supply_toner_yellow"],
)
graph_supply_toner_black = graphs.Graph(
    name="supply_toner_black",
    title=Title("Supply toner black"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=["supply_toner_black"],
)
