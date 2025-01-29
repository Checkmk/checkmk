#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_fc_crc_errors = metrics.Metric(
    name="fc_crc_errors",
    title=Title("Receive CRC errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_fc_c3discards = metrics.Metric(
    name="fc_c3discards",
    title=Title("C3 discards"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_fc_notxcredits = metrics.Metric(
    name="fc_notxcredits",
    title=Title("No TX Credits"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_fc_encouts = metrics.Metric(
    name="fc_encouts",
    title=Title("Enc-Outs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_fc_encins = metrics.Metric(
    name="fc_encins",
    title=Title("Enc-Ins"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_fc_bbcredit_zero = metrics.Metric(
    name="fc_bbcredit_zero",
    title=Title("BBcredit zero"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)

graph_fc_errors = graphs.Graph(
    name="fc_errors",
    title=Title("Errors"),
    compound_lines=[
        "fc_crc_errors",
        "fc_c3discards",
        "fc_notxcredits",
        "fc_encouts",
        "fc_encins",
        "fc_bbcredit_zero",
    ],
    optional=[
        "fc_encins",
        "fc_bbcredit_zero",
    ],
)
