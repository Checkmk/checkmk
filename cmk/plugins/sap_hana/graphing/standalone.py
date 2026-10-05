#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_num_high_alerts = metrics.Metric(
    name="num_high_alerts",
    title=Title("High alerts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_num_disabled_alerts = metrics.Metric(
    name="num_disabled_alerts",
    title=Title("Disabled alerts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
