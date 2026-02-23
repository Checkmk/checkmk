#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.graphing.v1 import metrics, perfometers, Title

metric_signal_power = metrics.Metric(
    name="signal_power",
    title=Title("Signal power"),
    unit=metrics.Unit(metrics.DecimalNotation("dBm")),
    color=metrics.Color.GREEN,
)

perfometer_signal_power = perfometers.Perfometer(
    name="signal_power",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(30),
    ),
    segments=["signal_power"],
)
