#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_queries_per_sec = metrics.Metric(
    name="queries_per_sec",
    title=Title("Queries per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_queries_per_sec = perfometers.Perfometer(
    name="queries_per_sec",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(2000),
    ),
    segments=["queries_per_sec"],
)
