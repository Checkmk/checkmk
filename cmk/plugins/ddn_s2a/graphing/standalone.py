#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_disk_min_read_wait = metrics.Metric(
    name="disk_min_read_wait",
    title=Title("Minimum read wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_disk_max_read_wait = metrics.Metric(
    name="disk_max_read_wait",
    title=Title("Maximum read wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_disk_min_write_wait = metrics.Metric(
    name="disk_min_write_wait",
    title=Title("Minimum write wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_disk_max_write_wait = metrics.Metric(
    name="disk_max_write_wait",
    title=Title("Maximum write wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
