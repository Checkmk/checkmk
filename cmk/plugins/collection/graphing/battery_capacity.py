#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_battery_capacity = metrics.Metric(
    name="battery_capacity",
    title=Title("Battery capacity"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)

perfometer_battery_capacity = perfometers.Perfometer(
    name="battery_capacity",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["battery_capacity"],
)

graph_battery_capacity = graphs.Graph(
    name="battery_capacity",
    title=Title("Battery capacity"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["battery_capacity"],
)
