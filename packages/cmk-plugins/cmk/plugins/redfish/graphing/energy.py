#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_ELECTRICAL_ENERGY = metrics.Unit(metrics.DecimalNotation("Wh"), metrics.AutoPrecision(3))

metric_energy = metrics.Metric(
    name="energy",
    title=Title("Electrical energy"),
    unit=UNIT_ELECTRICAL_ENERGY,
    color=metrics.Color.PINK,
)

perfometer_energy = perfometers.Perfometer(
    name="energy",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20000),
    ),
    segments=["energy"],
)
