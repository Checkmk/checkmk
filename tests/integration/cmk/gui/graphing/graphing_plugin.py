#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

metric_int_test = metrics.Metric(
    name="int_test",
    title=Title("Integration test metric"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.LIGHT_BLUE,
)
