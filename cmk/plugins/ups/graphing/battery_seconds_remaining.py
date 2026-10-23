#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_battery_seconds_remaining = metrics.Metric(
    name="battery_seconds_remaining",
    title=Title("Battery time remaining"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)

perfometer_battery_seconds_remaining = perfometers.Perfometer(
    name="battery_seconds_remaining",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(4000),
    ),
    segments=["battery_seconds_remaining"],
)
