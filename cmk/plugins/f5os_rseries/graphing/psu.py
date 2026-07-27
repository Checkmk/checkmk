#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Graphing for F5OS rSeries PSU power (input/output).

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer

_UNIT_WATT = Unit(DecimalNotation(" W"), StrictPrecision(0))

metric_f5os_psu_power_out = Metric(
    name="psu_power_out",
    title=Title("PSU output power"),
    unit=_UNIT_WATT,
    color=Color.BLUE,
)

metric_f5os_psu_power_in = Metric(
    name="psu_power_in",
    title=Title("PSU input power"),
    unit=_UNIT_WATT,
    color=Color.PURPLE,
)

graph_f5os_rseries_psu_power = Graph(
    name="f5os_rseries_psu_power",
    title=Title("F5OS PSU power"),
    simple_lines=["psu_power_in", "psu_power_out"],
)

perfometer_f5os_psu_power_out = Perfometer(
    name="f5os_psu_power_out",
    focus_range=FocusRange(Closed(0), Open(500)),
    segments=["psu_power_out"],
)
