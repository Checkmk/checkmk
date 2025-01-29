#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_fc_tx_frames = metrics.Metric(
    name="fc_tx_frames",
    title=Title("Transmitted Frames"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_fc_rx_frames = metrics.Metric(
    name="fc_rx_frames",
    title=Title("Received Frames"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_frames = graphs.Bidirectional(
    name="frames",
    title=Title("Frames"),
    lower=graphs.Graph(
        name="frames_tx",
        title=Title("Frames"),
        compound_lines=["fc_tx_frames"],
    ),
    upper=graphs.Graph(
        name="frames_rx",
        title=Title("Frames"),
        compound_lines=["fc_rx_frames"],
    ),
)
