#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_nimble_write_latency_total = metrics.Metric(
    name="nimble_write_latency_total",
    title=Title("Total write latency"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_nimble_write_latency_total = perfometers.Perfometer(
    name="nimble_write_latency_total",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20),
    ),
    segments=["nimble_write_latency_total"],
)
