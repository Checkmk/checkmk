#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
'''Perf-o-meter definition for PSUs'''

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
