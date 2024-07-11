#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_oracle_count = metrics.Metric(
    name="oracle_count",
    title=Title("Oracle count"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_oracle_count = perfometers.Perfometer(
    name="oracle_count",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(500),
    ),
    segments=["oracle_count"],
)
