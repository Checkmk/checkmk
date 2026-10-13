#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_packages_accepted = metrics.Metric(
    name="packages_accepted",
    title=Title("Accepted packages/s"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_packages_blocked = metrics.Metric(
    name="packages_blocked",
    title=Title("Blocked packages/s"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_packages_icmp_total = metrics.Metric(
    name="packages_icmp_total",
    title=Title("ICMP packages/s"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
