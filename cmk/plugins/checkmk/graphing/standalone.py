#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_average_sync_time = metrics.Metric(
    name="average_sync_time",
    title=Title("Average remote site sync time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_average_processing_time = metrics.Metric(
    name="average_processing_time",
    title=Title("Event processing time"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_PINK,
)
metric_average_rule_hit_ratio = metrics.Metric(
    name="average_rule_hit_ratio",
    title=Title("Rule hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GRAY,
)
metric_deferred_age = metrics.Metric(
    name="deferred_age",
    title=Title("Deferred files age"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)
