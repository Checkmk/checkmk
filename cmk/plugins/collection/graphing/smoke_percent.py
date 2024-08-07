#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_smoke_perc = metrics.Metric(
    name="smoke_perc",
    title=Title("Smoke"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)

perfometer_smoke_perc = perfometers.Perfometer(
    name="smoke_perc",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["smoke_perc"],
)
