#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BAR = metrics.Unit(metrics.DecimalNotation("bar"), metrics.AutoPrecision(4))

metric_pressure = metrics.Metric(
    name="pressure",
    title=Title("Pressure"),
    unit=UNIT_BAR,
    color=metrics.Color.ORANGE,
)

perfometer_pressure = perfometers.Perfometer(
    name="pressure",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["pressure"],
)
