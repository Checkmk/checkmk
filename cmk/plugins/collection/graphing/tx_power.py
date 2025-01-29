#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

metric_tx_power = metrics.Metric(
    name="tx_power",
    title=Title("Transmit power"),
    unit=metrics.Unit(metrics.DecimalNotation("dBmV")),
    color=metrics.Color.ORANGE,
)

perfometer_tx_power = perfometers.Perfometer(
    name="tx_power",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(100)),
    segments=["tx_power"],
)
