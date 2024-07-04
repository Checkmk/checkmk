#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_active_vms = metrics.Metric(
    name="active_vms",
    title=Title("Active VMs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

perfometer_active_vms = perfometers.Perfometer(
    name="active_vms",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(200),
    ),
    segments=["active_vms"],
)
