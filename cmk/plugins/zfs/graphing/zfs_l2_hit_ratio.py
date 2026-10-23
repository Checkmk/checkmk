#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_zfs_l2_hit_ratio = metrics.Metric(
    name="zfs_l2_hit_ratio",
    title=Title("L2 cache hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_zfs_l2_hit_ratio = perfometers.Perfometer(
    name="zfs_l2_hit_ratio",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["zfs_l2_hit_ratio"],
)
