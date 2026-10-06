#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_DECIBEL_MILLIWATTS = metrics.Unit(metrics.DecimalNotation("dBm"))

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
    title=Title("Temperature Lane 1"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.CYAN,
)
metric_port_temp_1 = metrics.Metric(
    name="port_temp_1",
    title=Title("Temperature Lane 2"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_YELLOW,
)
metric_port_temp_2 = metrics.Metric(
    name="port_temp_2",
    title=Title("Temperature Lane 3"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_PINK,
)
metric_port_temp_3 = metrics.Metric(
    name="port_temp_3",
    title=Title("Temperature Lane 4"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_BLUE,
)
metric_port_temp_4 = metrics.Metric(
    name="port_temp_4",
    title=Title("Temperature Lane 5"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.BLUE,
)
metric_port_temp_5 = metrics.Metric(
    name="port_temp_5",
    title=Title("Temperature Lane 6"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.YELLOW,
)
metric_port_temp_6 = metrics.Metric(
    name="port_temp_6",
    title=Title("Temperature Lane 7"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_port_temp_7 = metrics.Metric(
    name="port_temp_7",
    title=Title("Temperature Lane 8"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.PURPLE,
)
metric_port_temp_8 = metrics.Metric(
    name="port_temp_8",
    title=Title("Temperature Lane 9"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.CYAN,
)
metric_port_temp_9 = metrics.Metric(
    name="port_temp_9",
    title=Title("Temperature Lane 10"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_YELLOW,
)
