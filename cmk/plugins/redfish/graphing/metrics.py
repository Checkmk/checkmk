#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
'''Metric definition for PSUs'''
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from cmk.graphing.v1 import metrics, Title

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

metric_input_voltage = metrics.Metric(
    name="input_voltage",
    title=Title("Electrical input voltage"),
    unit=metrics.Unit(metrics.DecimalNotation("Volt")),
    color=metrics.Color.GREEN,
)
