#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_messages_in_queue = metrics.Metric(
    name="messages_in_queue",
    title=Title("Messages in queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

perfometer_messages_in_queue = perfometers.Perfometer(
    name="messages_in_queue",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["messages_in_queue"],
)
