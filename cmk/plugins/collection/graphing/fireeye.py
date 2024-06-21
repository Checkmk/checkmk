#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_analyzed_rate = metrics.Metric(
    name="analyzed_rate",
    title=Title("Analyzed per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_bypass_rate = metrics.Metric(
    name="bypass_rate",
    title=Title("Bypass per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_fireeye_stat_attachment = metrics.Metric(
    name="fireeye_stat_attachment",
    title=Title("Emails containing Attachment per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_fireeye_stat_maliciousattachment = metrics.Metric(
    name="fireeye_stat_maliciousattachment",
    title=Title("Emails containing Malicious Attachment per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_fireeye_stat_maliciousurl = metrics.Metric(
    name="fireeye_stat_maliciousurl",
    title=Title("Emails containing Malicious URL per second"),
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
metric_total_rate = metrics.Metric(
    name="total_rate",
    title=Title("Total per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_total_rate = perfometers.Perfometer(
    name="total_rate",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(90),
    ),
    segments=["total_rate"],
)
perfometer_bypass_rate = perfometers.Perfometer(
    name="bypass_rate",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(3),
    ),
    segments=["bypass_rate"],
)
perfometer_fireeye_stat_attachment = perfometers.Perfometer(
    name="fireeye_stat_attachment",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(90),
    ),
    segments=["fireeye_stat_attachment"],
)
