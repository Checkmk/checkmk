#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_db_read_latency_s = metrics.Metric(
    name="db_read_latency_s",
    title=Title("Read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)

metric_db_read_recovery_latency_s = metrics.Metric(
    name="db_read_recovery_latency_s",
    title=Title("Read recovery latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_GREEN,
)

metric_db_write_latency_s = metrics.Metric(
    name="db_write_latency_s",
    title=Title("Write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_BLUE,
)

metric_db_log_latency_s = metrics.Metric(
    name="db_log_latency_s",
    title=Title("Log latency"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_YELLOW,
)
