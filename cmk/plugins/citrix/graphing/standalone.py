#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_registered_desktops = metrics.Metric(
    name="registered_desktops",
    title=Title("Registered desktops"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_inactive_sessions = metrics.Metric(
    name="inactive_sessions",
    title=Title("Inactive sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
