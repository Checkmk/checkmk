#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_util1s = metrics.Metric(
    name="util1s",
    title=Title("CPU utilization last second"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_util5s = metrics.Metric(
    name="util5s",
    title=Title("CPU utilization last five seconds"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
