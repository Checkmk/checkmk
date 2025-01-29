#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_graylog_diff = metrics.Metric(
    name="graylog_diff",
    title=Title("Number of messages in defined timespan"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
