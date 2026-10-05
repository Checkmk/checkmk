#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hours_operation = metrics.Metric(
    name="hours_operation",
    title=Title("Hours of operation"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
metric_hours_since_service = metrics.Metric(
    name="hours_since_service",
    title=Title("Hours since service"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
