#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_DECIBEL_MILLIWATTS = metrics.Unit(metrics.DecimalNotation("dBm"))

metric_rx_light = metrics.Metric(
    name="rx_light",
    title=Title("RX Signal Power"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.BLUE,
)
metric_tx_light = metrics.Metric(
    name="tx_light",
    title=Title("TX Signal Power"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.GREEN,
)

graph_optical_signal_power = graphs.Graph(
    name="optical_signal_power",
    title=Title("Optical Signal Power"),
    simple_lines=[
        "rx_light",
        "tx_light",
    ],
)
