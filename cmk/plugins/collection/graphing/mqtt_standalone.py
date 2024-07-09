#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_connections_opened_received_rate = metrics.Metric(
    name="connections_opened_received_rate",
    title=Title("Connections opened"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_subscriptions = metrics.Metric(
    name="subscriptions",
    title=Title("Current subscriptions"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_retained_messages = metrics.Metric(
    name="retained_messages",
    title=Title("Retained messages"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)
metric_stored_messages = metrics.Metric(
    name="stored_messages",
    title=Title("Stored messages"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)
metric_stored_messages_bytes = metrics.Metric(
    name="stored_messages_bytes",
    title=Title("Size of stored messages"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
