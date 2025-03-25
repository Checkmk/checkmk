#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENT = metrics.Unit(metrics.DecimalNotation("%"))

metric_queue_utilization = metrics.Metric(
    name="cisco_sma_queue_utilization",
    title=Title("Utilization"),
    unit=UNIT_PERCENT,
    color=metrics.Color.DARK_BLUE,
)

perfometer_queue_utilization = perfometers.Perfometer(
    name="cisco_sma_queue_utilization_perfometer",
    focus_range=perfometers.FocusRange(
        lower=perfometers.Closed(0),
        upper=perfometers.Open(100),
    ),
    segments=["cisco_sma_queue_utilization"],
)
