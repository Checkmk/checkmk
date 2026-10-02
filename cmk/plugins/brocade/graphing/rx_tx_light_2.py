#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_DECIBEL_MILLIWATTS = metrics.Unit(metrics.DecimalNotation("dBm"))

metric_rx_light_2 = metrics.Metric(
    name="rx_light_2",
    title=Title("RX signal power lane 2"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.BLUE,
)
metric_tx_light_2 = metrics.Metric(
    name="tx_light_2",
    title=Title("TX signal power lane 2"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.GREEN,
)

graph_optical_signal_power_2 = graphs.Graph(
    name="optical_signal_power_lane_2",
    title=Title("Optical signal power lane 2"),
    simple_lines=[
        "rx_light_2",
        "tx_light_2",
    ],
)
