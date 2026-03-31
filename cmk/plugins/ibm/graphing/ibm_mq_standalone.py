#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_curdepth = metrics.Metric(
    name="curdepth",
    title=Title("Queue depth"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_msgage = metrics.Metric(
    name="msgage",
    title=Title("Age of oldest message"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
