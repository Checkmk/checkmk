#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric definitions for Redfish power consumption monitoring"""

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

# Power consumption metrics for up to 4 systems (system IDs 0-3)
_POWER_UNIT = metrics.Unit(metrics.DecimalNotation("W"))

metric_averageconsumedwatts_0 = metrics.Metric(
    name="averageconsumedwatts_0",
    title=Title("System 0 average consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.BLUE,
)
metric_minconsumedwatts_0 = metrics.Metric(
    name="minconsumedwatts_0",
    title=Title("System 0 minimum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.LIGHT_BLUE,
)
metric_maxconsumedwatts_0 = metrics.Metric(
    name="maxconsumedwatts_0",
    title=Title("System 0 maximum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.DARK_BLUE,
)

metric_averageconsumedwatts_1 = metrics.Metric(
    name="averageconsumedwatts_1",
    title=Title("System 1 average consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.GREEN,
)
metric_minconsumedwatts_1 = metrics.Metric(
    name="minconsumedwatts_1",
    title=Title("System 1 minimum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.LIGHT_GREEN,
)
metric_maxconsumedwatts_1 = metrics.Metric(
    name="maxconsumedwatts_1",
    title=Title("System 1 maximum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.DARK_GREEN,
)

metric_averageconsumedwatts_2 = metrics.Metric(
    name="averageconsumedwatts_2",
    title=Title("System 2 average consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.ORANGE,
)
metric_minconsumedwatts_2 = metrics.Metric(
    name="minconsumedwatts_2",
    title=Title("System 2 minimum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_maxconsumedwatts_2 = metrics.Metric(
    name="maxconsumedwatts_2",
    title=Title("System 2 maximum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.DARK_ORANGE,
)

metric_averageconsumedwatts_3 = metrics.Metric(
    name="averageconsumedwatts_3",
    title=Title("System 3 average consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.PURPLE,
)
metric_minconsumedwatts_3 = metrics.Metric(
    name="minconsumedwatts_3",
    title=Title("System 3 minimum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_maxconsumedwatts_3 = metrics.Metric(
    name="maxconsumedwatts_3",
    title=Title("System 3 maximum consumed watts"),
    unit=_POWER_UNIT,
    color=metrics.Color.DARK_PURPLE,
)

perfometer_averageconsumedwatts_0 = perfometers.Perfometer(
    name="averageconsumedwatts_0",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000.0)),
    segments=["averageconsumedwatts_0"],
)

graph_power_consumption = graphs.Graph(
    name="redfish_power_consumption",
    title=Title("Redfish Power Consumption"),
    simple_lines=[
        "averageconsumedwatts_0",
        "minconsumedwatts_0",
        "maxconsumedwatts_0",
        "averageconsumedwatts_1",
        "minconsumedwatts_1",
        "maxconsumedwatts_1",
        "averageconsumedwatts_2",
        "minconsumedwatts_2",
        "maxconsumedwatts_2",
        "averageconsumedwatts_3",
        "minconsumedwatts_3",
        "maxconsumedwatts_3",
    ],
)
