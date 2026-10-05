#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_zfs_l2_size = metrics.Metric(
    name="zfs_l2_size",
    title=Title("L2 cache size"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
