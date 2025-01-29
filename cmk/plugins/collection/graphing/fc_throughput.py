#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_fc_tx_bytes = metrics.Metric(
    name="fc_tx_bytes",
    title=Title("Output"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_fc_rx_bytes = metrics.Metric(
    name="fc_rx_bytes",
    title=Title("Input"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

perfometer_fc_bytes = perfometers.Bidirectional(
    name="fc_bytes",
    left=perfometers.Perfometer(
        name="fc_rx_bytes",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(60000000),
        ),
        segments=["fc_rx_bytes"],
    ),
    right=perfometers.Perfometer(
        name="fc_tx_bytes",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(60000000),
        ),
        segments=["fc_tx_bytes"],
    ),
)

graph_throughput = graphs.Bidirectional(
    name="throughput",
    title=Title("Throughput"),
    lower=graphs.Graph(
        name="throughput_tx",
        title=Title("Throughput"),
        compound_lines=["fc_tx_bytes"],
    ),
    upper=graphs.Graph(
        name="throughput_rx",
        title=Title("Throughput"),
        compound_lines=["fc_rx_bytes"],
    ),
)
