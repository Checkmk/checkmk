#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_data_usage = metrics.Metric(
    name="data_usage",
    title=Title("Data usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_meta_usage = metrics.Metric(
    name="meta_usage",
    title=Title("Meta usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
