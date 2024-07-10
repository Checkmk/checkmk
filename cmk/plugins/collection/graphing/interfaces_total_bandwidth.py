#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BITS_PER_SECOND = metrics.Unit(metrics.IECNotation("bits/s"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_if_total_bps = metrics.Metric(
    name="if_total_bps",
    title=Title("Total bandwidth (sum of in and out)"),
    unit=UNIT_BITS_PER_SECOND,
    color=metrics.Color.GREEN,
)
