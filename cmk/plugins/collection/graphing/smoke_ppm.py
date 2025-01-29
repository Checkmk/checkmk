#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE_PER_METER = metrics.Unit(metrics.DecimalNotation("%/m"))

metric_smoke_ppm = metrics.Metric(
    name="smoke_ppm",
    title=Title("Smoke"),
    unit=UNIT_PERCENTAGE_PER_METER,
    color=metrics.Color.LIGHT_GREEN,
)

perfometer_smoke_ppm = perfometers.Perfometer(
    name="smoke_ppm",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(10),
    ),
    segments=["smoke_ppm"],
)
