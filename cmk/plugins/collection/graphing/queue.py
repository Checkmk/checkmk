#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

metric_queue_length = metrics.Metric(
    name="queue_length",
    title=Title("Queue length"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(0)),
    color=metrics.Color.LIGHT_BLUE,
)

perfometer_queue_length = perfometers.Perfometer(
    name="queue_length",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(200)),
    segments=["queue_length"],
)
