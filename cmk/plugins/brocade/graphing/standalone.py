#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_DEGREE_CELSIUS = metrics.Unit(metrics.DecimalNotation("°C"))

metric_util1s = metrics.Metric(
    name="util1s",
    title=Title("CPU utilization last second"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_util5s = metrics.Metric(
    name="util5s",
    title=Title("CPU utilization last five seconds"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_port_temp_0 = metrics.Metric(
    name="port_temp_0",
    title=Title("Temperature lane 0"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.CYAN,
)
metric_port_temp_1 = metrics.Metric(
    name="port_temp_1",
    title=Title("Temperature lane 1"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.DARK_YELLOW,
)
metric_port_temp_2 = metrics.Metric(
    name="port_temp_2",
    title=Title("Temperature lane 2"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.DARK_PINK,
)
metric_port_temp_3 = metrics.Metric(
    name="port_temp_3",
    title=Title("Temperature lane 3"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.DARK_BLUE,
)
metric_port_temp_4 = metrics.Metric(
    name="port_temp_4",
    title=Title("Temperature lane 4"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.BLUE,
)
metric_port_temp_5 = metrics.Metric(
    name="port_temp_5",
    title=Title("Temperature lane 5"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.YELLOW,
)
metric_port_temp_6 = metrics.Metric(
    name="port_temp_6",
    title=Title("Temperature lane 6"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_port_temp_7 = metrics.Metric(
    name="port_temp_7",
    title=Title("Temperature lane 7"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.PURPLE,
)
metric_port_temp_8 = metrics.Metric(
    name="port_temp_8",
    title=Title("Temperature lane 8"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.CYAN,
)
metric_port_temp_9 = metrics.Metric(
    name="port_temp_9",
    title=Title("Temperature lane 9"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.DARK_YELLOW,
)
