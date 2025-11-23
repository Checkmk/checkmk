#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric definition for PSUs"""

from cmk.graphing.v1 import metrics, perfometers, Title

metric_input_power = metrics.Metric(
    name="input_power",
    title=Title("Electrical input power"),
    unit=metrics.Unit(metrics.DecimalNotation("Watt")),
    color=metrics.Color.BROWN,
)

metric_output_power = metrics.Metric(
    name="output_power",
    title=Title("Electrical output power"),
    unit=metrics.Unit(metrics.DecimalNotation("Watt")),
    color=metrics.Color.BLUE,
)

perfometer_input_output_power = perfometers.Stacked(
    name="power_summary",
    lower=perfometers.Perfometer(
        name=metric_input_power.name,
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(500.0)),
        segments=[metric_input_power.name],
    ),
    upper=perfometers.Perfometer(
        name=metric_output_power.name,
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(500.0)),
        segments=[metric_output_power.name],
    ),
)
