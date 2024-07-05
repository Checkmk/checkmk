#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_AMPERE = metrics.Unit(metrics.DecimalNotation("A"), metrics.AutoPrecision(3))

metric_battery_current = metrics.Metric(
    name="battery_current",
    title=Title("Battery electrical current"),
    unit=UNIT_AMPERE,
    color=metrics.Color.ORANGE,
)
metric_current = metrics.Metric(
    name="current",
    title=Title("Electrical current"),
    unit=UNIT_AMPERE,
    color=metrics.Color.LIGHT_ORANGE,
)

perfometer_current = perfometers.Perfometer(
    name="current",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20),
    ),
    segments=["current"],
)

graph_battery_currents = graphs.Graph(
    name="battery_currents",
    title=Title("Battery currents"),
    compound_lines=[
        "battery_current",
        "current",
    ],
)
