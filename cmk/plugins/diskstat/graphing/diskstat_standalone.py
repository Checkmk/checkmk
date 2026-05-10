#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_disk_average_wait = metrics.Metric(
    name="disk_average_wait",
    title=Title("Request wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

metric_disk_average_request_size = metrics.Metric(
    name="disk_average_request_size",
    title=Title("Average request size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

metric_disk_latency = metrics.Metric(
    name="disk_latency",
    title=Title("Average disk latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_PINK,
)

metric_disk_queue_length = metrics.Metric(
    name="disk_queue_length",
    title=Title("Average disk I/O-queue length"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
