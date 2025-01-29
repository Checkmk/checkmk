#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_mobileiron_policyviolationcount = metrics.Metric(
    name="mobileiron_policyviolationcount",
    title=Title("Policy violation count"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)

perfometer_mobileiron_policyviolationcount = perfometers.Perfometer(
    name="mobileiron_policyviolationcount",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(6),
    ),
    segments=["mobileiron_policyviolationcount"],
)
