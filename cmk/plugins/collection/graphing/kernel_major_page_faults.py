#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_major_page_faults = metrics.Metric(
    name="major_page_faults",
    title=Title("Major page faults"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

perfometer_major_page_faults = perfometers.Perfometer(
    name="major_page_faults",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(2000)),
    segments=["major_page_faults"],
)
