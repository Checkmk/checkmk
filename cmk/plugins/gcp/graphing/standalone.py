#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_SECONDS_PER_SECOND = metrics.Unit(metrics.DecimalNotation("s/s"))

metric_faas_active_instance_count = metrics.Metric(
    name="faas_active_instance_count",
    title=Title("Number of active instances"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_faas_execution_count = metrics.Metric(
    name="faas_execution_count",
    title=Title("Number of requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_faas_execution_count_2xx = metrics.Metric(
    name="faas_execution_count_2xx",
    title=Title("Number of requests with return code class 2xx (success)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_faas_execution_count_3xx = metrics.Metric(
    name="faas_execution_count_3xx",
    title=Title("Number of requests with return code class 3xx (redirection)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_faas_execution_count_4xx = metrics.Metric(
    name="faas_execution_count_4xx",
    title=Title("Number of requests with return code class 4xx (client error)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_faas_execution_count_5xx = metrics.Metric(
    name="faas_execution_count_5xx",
    title=Title("Number of requests with return code class 5xx (server error)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_faas_total_instance_count = metrics.Metric(
    name="faas_total_instance_count",
    title=Title("Total number of instances"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_gcp_billable_time = metrics.Metric(
    name="gcp_billable_time",
    title=Title("Billable time"),
    unit=UNIT_SECONDS_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
