#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_snapshot_reserve_used_percent = metrics.Metric(
    name="snapshot_reserve_used_percent",
    title=Title("Snapshot reserve used %"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

perfometer_snapshot_reserve_used_percent = perfometers.Perfometer(
    name="snapshot_reserve_used_percent",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["snapshot_reserve_used_percent"],
)
