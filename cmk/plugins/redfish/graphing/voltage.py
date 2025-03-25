#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric definition for PSUs"""

from cmk.graphing.v1 import metrics, Title

metric_input_voltage = metrics.Metric(
    name="input_voltage",
    title=Title("Electrical input voltage"),
    unit=metrics.Unit(metrics.DecimalNotation("Volt")),
    color=metrics.Color.GREEN,
)
