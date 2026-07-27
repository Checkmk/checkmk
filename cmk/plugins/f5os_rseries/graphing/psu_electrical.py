#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Standalone metric definitions for F5OS rSeries PSU input current and voltage.
#
# These are recorded per PSU but do not share an axis with each other or with the
# power metrics, so they are defined without a graph or perf-o-meter of their own.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

metric_f5os_psu_current_in = Metric(
    name="psu_current_in",
    title=Title("PSU input current"),
    unit=Unit(DecimalNotation(" A"), StrictPrecision(2)),
    color=Color.GREEN,
)

metric_f5os_psu_voltage_in = Metric(
    name="psu_voltage_in",
    title=Title("PSU input voltage"),
    unit=Unit(DecimalNotation(" V"), StrictPrecision(0)),
    color=Color.CYAN,
)
