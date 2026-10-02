#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PASCAL = metrics.Unit(metrics.DecimalNotation("Pa"), metrics.AutoPrecision(3))

metric_pressure_pa = metrics.Metric(
    name="pressure_pa",
    title=Title("Pressure"),
    unit=UNIT_PASCAL,
    color=metrics.Color.ORANGE,
)

perfometer_pressure_pa = perfometers.Perfometer(
    name="pressure_pa",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20),
    ),
    segments=["pressure_pa"],
)
