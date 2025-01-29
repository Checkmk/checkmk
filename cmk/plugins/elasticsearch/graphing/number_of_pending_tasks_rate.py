#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_number_of_pending_tasks_rate = metrics.Metric(
    name="number_of_pending_tasks_rate",
    title=Title("Pending tasks delta"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

perfometer_number_of_pending_tasks_rate = perfometers.Perfometer(
    name="number_of_pending_tasks_rate",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20),
    ),
    segments=["number_of_pending_tasks_rate"],
)
