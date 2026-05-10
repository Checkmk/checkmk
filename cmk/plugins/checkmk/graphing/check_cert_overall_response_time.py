#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_overall_response_time = metrics.Metric(
    name="overall_response_time",
    title=Title("Overall response time"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
