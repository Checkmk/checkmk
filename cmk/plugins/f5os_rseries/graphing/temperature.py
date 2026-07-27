#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Graphing for F5OS rSeries temperature checks.
#
# The current reading uses the shared ``temp`` metric (cmk.plugins.lib.temperature),
# which is defined centrally; here we add the platform's average and maximum readings.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

_UNIT_CELSIUS = Unit(DecimalNotation(" °C"), StrictPrecision(1))

metric_f5os_temp_avg = Metric(
    name="temp_avg",
    title=Title("Temperature (average)"),
    unit=_UNIT_CELSIUS,
    color=Color.ORANGE,
)

metric_f5os_temp_max = Metric(
    name="temp_max",
    title=Title("Temperature (maximum)"),
    unit=_UNIT_CELSIUS,
    color=Color.RED,
)

graph_f5os_rseries_temp = Graph(
    name="f5os_rseries_temp",
    title=Title("F5OS platform temperature"),
    simple_lines=["temp_avg", "temp_max"],
)
