#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_job_duration = metrics.Metric(
    name="job_duration",
    title=Title("Job duration"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

perfometer_job_duration = perfometers.Perfometer(
    name="job_duration",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(300),
    ),
    segments=["job_duration"],
)
