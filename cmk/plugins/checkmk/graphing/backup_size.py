#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_backup_size = metrics.Metric(
    name="backup_size",
    title=Title("Backup size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_backup_size = perfometers.Perfometer(
    name="backup_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(300000000000),
    ),
    segments=["backup_size"],
)
