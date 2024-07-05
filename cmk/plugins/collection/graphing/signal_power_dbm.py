#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_DECIBEL_MILLIWATTS = metrics.Unit(metrics.DecimalNotation("dBm"))

metric_input_signal_power_dbm = metrics.Metric(
    name="input_signal_power_dbm",
    title=Title("Input power"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.BLUE,
)
metric_output_signal_power_dbm = metrics.Metric(
    name="output_signal_power_dbm",
    title=Title("Output power"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.GREEN,
)

perfometer_input_signal_power_dbm_output_signal_power_dbm = perfometers.Bidirectional(
    name="input_signal_power_dbm_output_signal_power_dbm",
    left=perfometers.Perfometer(
        name="input_signal_power_dbm",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(6),
        ),
        segments=["input_signal_power_dbm"],
    ),
    right=perfometers.Perfometer(
        name="output_signal_power_dbm",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(6),
        ),
        segments=["output_signal_power_dbm"],
    ),
)
