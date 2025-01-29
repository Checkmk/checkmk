#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_REVOLUTIONS_PER_MINUTE = metrics.Unit(metrics.DecimalNotation("rpm"), metrics.AutoPrecision(4))

metric_fan = metrics.Metric(
    name="fan",
    title=Title("Fan speed"),
    unit=UNIT_REVOLUTIONS_PER_MINUTE,
    color=metrics.Color.ORANGE,
)

perfometer_fan = perfometers.Perfometer(
    name="fan",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(6000),
    ),
    segments=["fan"],
)
