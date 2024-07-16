#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_privileged = metrics.Metric(
    name="privileged",
    title=Title("Privileged"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
