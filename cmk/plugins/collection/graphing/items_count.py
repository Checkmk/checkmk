#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_items_count = metrics.Metric(
    name="items_count",
    title=Title("Items"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)

perfometer_items_count = perfometers.Perfometer(
    name="items_count",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(2000),
    ),
    segments=["items_count"],
)
