#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_fireeye_stat_attachment = metrics.Metric(
    name="fireeye_stat_attachment",
    title=Title("Emails containing attachment per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

perfometer_fireeye_stat_attachment = perfometers.Perfometer(
    name="fireeye_stat_attachment",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(90),
    ),
    segments=["fireeye_stat_attachment"],
)
