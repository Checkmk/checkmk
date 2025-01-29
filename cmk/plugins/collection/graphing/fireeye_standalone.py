#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_analyzed_rate = metrics.Metric(
    name="analyzed_rate",
    title=Title("Analyzed per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_fireeye_stat_maliciousattachment = metrics.Metric(
    name="fireeye_stat_maliciousattachment",
    title=Title("Emails containing malicious attachment per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_fireeye_stat_maliciousurl = metrics.Metric(
    name="fireeye_stat_maliciousurl",
    title=Title("Emails containing malicious URL per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GRAY,
)
metric_fireeye_stat_url = metrics.Metric(
    name="fireeye_stat_url",
    title=Title("Emails containing URL per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_infected_rate = metrics.Metric(
    name="infected_rate",
    title=Title("Infected per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GRAY,
)
