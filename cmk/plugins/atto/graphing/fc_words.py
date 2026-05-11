#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_fc_rx_words = metrics.Metric(
    name="fc_rx_words",
    title=Title("Received Words"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_fc_tx_words = metrics.Metric(
    name="fc_tx_words",
    title=Title("Transmitted Words"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_words_words = graphs.Bidirectional(
    name="words",
    title=Title("Words"),
    lower=graphs.Graph(
        name="words_tx",
        title=Title("Words"),
        compound_lines=["fc_tx_words"],
    ),
    upper=graphs.Graph(
        name="words_rx",
        title=Title("Words"),
        compound_lines=["fc_rx_words"],
    ),
)
