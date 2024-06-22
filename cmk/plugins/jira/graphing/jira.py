#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_jira_count = metrics.Metric(
    name="jira_count",
    title=Title("Number of issues"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_jira_sum = metrics.Metric(
    name="jira_sum",
    title=Title("Result of summed up values"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_jira_avg = metrics.Metric(
    name="jira_avg",
    title=Title("Average value"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_jira_diff = metrics.Metric(
    name="jira_diff",
    title=Title("Difference"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
