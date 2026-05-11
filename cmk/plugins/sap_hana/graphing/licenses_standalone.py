#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_license_usage = metrics.Metric(
    name="license_usage",
    title=Title("License usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_license_size = metrics.Metric(
    name="license_size",
    title=Title("Size of license"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
