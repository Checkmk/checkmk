#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_bypass_rate = metrics.Metric(
    name="bypass_rate",
    title=Title("Bypass per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)

perfometer_bypass_rate = perfometers.Perfometer(
    name="bypass_rate",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(3),
    ),
    segments=["bypass_rate"],
)
