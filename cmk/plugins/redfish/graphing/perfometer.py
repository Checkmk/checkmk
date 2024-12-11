#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
'''Perf-o-meter definition for PSUs'''
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from cmk.graphing.v1 import perfometers

perfometer_input_output_power = perfometers.Stacked(
    name="power_summary",
    lower=perfometers.Perfometer(
        name="input_power",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(500.0)),
        segments=["input_power"],
    ),
    upper=perfometers.Perfometer(
        name="output_power",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(500.0)),
        segments=["output_power"],
    ),
)
