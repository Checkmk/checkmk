#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_decoder_utilization = metrics.Metric(
    name="decoder_utilization",
    title=Title("Decoder utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_encoder_utilization = metrics.Metric(
    name="encoder_utilization",
    title=Title("Encoder utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_encoder_utilization_decoder_utilization = perfometers.Bidirectional(
    name="en_decoder_utilization",
    left=perfometers.Perfometer(
        name="encoder_utilization",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["encoder_utilization"],
    ),
    right=perfometers.Perfometer(
        name="decoder_utilization",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["decoder_utilization"],
    ),
)
