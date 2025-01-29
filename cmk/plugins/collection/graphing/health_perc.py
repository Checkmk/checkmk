#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_health_perc = metrics.Metric(
    name="health_perc",
    title=Title("Health"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

perfometer_health_perc = perfometers.Perfometer(
    name="health_perc",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["health_perc"],
)
