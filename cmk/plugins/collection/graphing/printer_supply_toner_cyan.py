#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_supply_toner_cyan = metrics.Metric(
    name="supply_toner_cyan",
    title=Title("Supply toner cyan"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)

perfometer_supply_toner_cyan = perfometers.Perfometer(
    name="supply_toner_cyan",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["supply_toner_cyan"],
)

graph_supply_toner_cyan = graphs.Graph(
    name="supply_toner_cyan",
    title=Title("Supply toner cyan"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=["supply_toner_cyan"],
)
