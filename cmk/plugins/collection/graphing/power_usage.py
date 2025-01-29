#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_ELECTRICAL_POWER = metrics.Unit(metrics.DecimalNotation("W"), metrics.AutoPrecision(3))

metric_power_usage = metrics.Metric(
    name="power_usage",
    title=Title("Power Usage"),
    unit=UNIT_ELECTRICAL_POWER,
    color=metrics.Color.PINK,
)

perfometer_power_usage = perfometers.Perfometer(
    name="power_usage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.MaximumOf(
                "power_usage",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["power_usage"],
)
