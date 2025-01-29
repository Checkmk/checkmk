#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_DEGREE_CELSIUS = metrics.Unit(metrics.DecimalNotation("°C"))

metric_temp = metrics.Metric(
    name="temp",
    title=Title("Temperature"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.ORANGE,
)

perfometer_temp = perfometers.Perfometer(
    name="temperature",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(70),
    ),
    segments=["temp"],
)

graph_temperature = graphs.Graph(
    name="temperature",
    title=Title("Temperature"),
    compound_lines=["temp"],
    simple_lines=[
        metrics.WarningOf("temp"),
        metrics.CriticalOf("temp"),
    ],
)
