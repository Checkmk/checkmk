#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_VOLTAGE = metrics.Unit(metrics.DecimalNotation("V"), metrics.AutoPrecision(3))

metric_voltage = metrics.Metric(
    name="voltage",
    title=Title("Electrical voltage"),
    unit=UNIT_VOLTAGE,
    color=metrics.Color.ORANGE,
)

perfometer_voltage = perfometers.Perfometer(
    name="voltage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(400),
    ),
    segments=["voltage"],
)
