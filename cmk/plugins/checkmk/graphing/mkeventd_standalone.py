#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_average_connect_rate = metrics.Metric(
    name="average_connect_rate",
    title=Title("Client connects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_average_event_rate = metrics.Metric(
    name="average_event_rate",
    title=Title("Event creations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_average_request_time = metrics.Metric(
    name="average_request_time",
    title=Title("Average request response time"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.ORANGE,
)
metric_num_open_events = metrics.Metric(
    name="num_open_events",
    title=Title("Current events"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)
