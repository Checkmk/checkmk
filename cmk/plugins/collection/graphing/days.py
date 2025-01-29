#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_DAYS = metrics.Unit(metrics.DecimalNotation("days"), metrics.StrictPrecision(2))

metric_days = metrics.Metric(
    name="days",
    title=Title("Days"),
    unit=UNIT_DAYS,
    color=metrics.Color.ORANGE,
)

perfometer_days = perfometers.Perfometer(
    name="days",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(200),
    ),
    segments=["days"],
)
