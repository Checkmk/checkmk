#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_DECIBEL = metrics.Unit(metrics.DecimalNotation("dB"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_codewords_corrected = metrics.Metric(
    name="codewords_corrected",
    title=Title("Corrected codewords"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_codewords_uncorrectable = metrics.Metric(
    name="codewords_uncorrectable",
    title=Title("Uncorrectable codewords"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.RED,
)
metric_signal_noise = metrics.Metric(
    name="signal_noise",
    title=Title("Signal/Noise ratio"),
    unit=UNIT_DECIBEL,
    color=metrics.Color.LIGHT_GREEN,
)

perfometer_codewords_corrected_codewords_uncorrectable_signal_noise = perfometers.Stacked(
    name="codewords_corrected_codewords_uncorrectable_signal_noise",
    lower=perfometers.Perfometer(
        name="codewords_corrected_codewords_uncorrectable",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(1.0),
        ),
        segments=[
            "codewords_corrected",
            "codewords_uncorrectable",
        ],
    ),
    upper=perfometers.Perfometer(
        name="signal_noise",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=["signal_noise"],
    ),
)
perfometer_signal_noise = perfometers.Perfometer(
    name="signal_noise",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(90),
    ),
    segments=["signal_noise"],
)
