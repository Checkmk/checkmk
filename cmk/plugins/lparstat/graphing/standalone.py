#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_app = metrics.Metric(
    name="app",
    title=Title("Available physical processors in shared pool"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_entc = metrics.Metric(
    name="entc",
    title=Title("Entitled capacity consumed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_lbusy = metrics.Metric(
    name="lbusy",
    title=Title("Logical processor(s) utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_nsp = metrics.Metric(
    name="nsp",
    title=Title("Average processor speed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_phint = metrics.Metric(
    name="phint",
    title=Title("Phantom interruptions received"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_physc = metrics.Metric(
    name="physc",
    title=Title("Physical processors consumed"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_utcyc = metrics.Metric(
    name="utcyc",
    title=Title("Unaccounted turbo cycles"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_vcsw = metrics.Metric(
    name="vcsw",
    title=Title("Virtual context switches"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
