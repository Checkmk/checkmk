#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import metrics, Title

UNIT_SECOND = metrics.Unit(metrics.TimeNotation())
UNIT_INTEGER = metrics.Unit(metrics.DecimalNotation(""))


metric_queue_length = metrics.Metric(
    name="cisco_sma_queue_length",
    title=Title("Queue Length"),
    unit=UNIT_INTEGER,
    color=metrics.Color.DARK_GREEN,
)

metric_queue_oldest_message_age = metrics.Metric(
    name="cisco_sma_queue_oldest_message_age",
    title=Title("Oldest Message Age"),
    unit=UNIT_SECOND,
    color=metrics.Color.DARK_ORANGE,
)
