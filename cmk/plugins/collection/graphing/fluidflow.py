#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_LITER_PER_SECOND = metrics.Unit(metrics.DecimalNotation("l/s"), metrics.AutoPrecision(3))

metric_fluidflow = metrics.Metric(
    name="fluidflow",
    title=Title("Fluid flow"),
    unit=UNIT_LITER_PER_SECOND,
    color=metrics.Color.ORANGE,
)

perfometer_fluidflow = perfometers.Perfometer(
    name="fluidflow",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["fluidflow"],
)
