#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_mem_pages_rate = metrics.Metric(
    name="mem_pages_rate",
    title=Title("Memory pages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_mem_pages_rate = perfometers.Perfometer(
    name="mem_pages_rate",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(9000),
    ),
    segments=["mem_pages_rate"],
)
