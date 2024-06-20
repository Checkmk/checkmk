#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

# Checks msexch_isclienttype, msexch_isstore and msexch_rcpclientaccess all report this metric
metric_average_latency_s = metrics.Metric(
    name="average_latency_s",
    title=Title("Average latency"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_BLUE,
)
