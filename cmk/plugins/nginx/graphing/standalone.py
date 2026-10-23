#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_handled = metrics.Metric(
    name="handled",
    title=Title("Handled connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_reading = metrics.Metric(
    name="reading",
    title=Title("Reading connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_waiting = metrics.Metric(
    name="waiting",
    title=Title("Waiting connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_writing = metrics.Metric(
    name="writing",
    title=Title("Writing connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
