#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

metric_active_since = metrics.Metric(
    name="active_since",
    title=Title("Active since"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.GRAY,
)

metric_number_of_tasks = metrics.Metric(
    name="number_of_tasks",
    title=Title("Number of tasks"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.GRAY,
)
