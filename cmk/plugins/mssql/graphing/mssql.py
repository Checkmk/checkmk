#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_database_job_duration = metrics.Metric(
    name="database_job_duration",
    title=Title("Job Duration"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_page_life_expectancy = metrics.Metric(
    name="page_life_expectancy",
    title=Title("Page Life Expectancy"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
