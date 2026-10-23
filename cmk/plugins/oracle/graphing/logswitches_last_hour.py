#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_logswitches_last_hour = metrics.Metric(
    name="logswitches_last_hour",
    title=Title("Log switches in the last 60 minutes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_logswitches_last_hour = perfometers.Perfometer(
    name="logswitches_last_hour",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(30),
    ),
    segments=["logswitches_last_hour"],
)
