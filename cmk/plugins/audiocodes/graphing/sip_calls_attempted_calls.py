#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_audiocodes_tel2ip_attempted_calls = metrics.Metric(
    name="audiocodes_tel2ip_attempted_calls",
    title=Title("Tel2IP Number of Attempted SIP/H323 calls"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_audiocodes_ip2tel_attempted_calls = metrics.Metric(
    name="audiocodes_ip2tel_attempted_calls",
    title=Title("IP2Tel Number of Attempted SIP/H323 calls"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

graph_audiocodes_sip_calls_attempted_calls = graphs.Bidirectional(
    name="audiocodes_sip_calls_attempted_calls",
    title=Title("Number of Attempted SIP/H323 calls"),
    lower=graphs.Graph(
        name="tel2ip_attempted_calls",
        title=Title("Tel2IP"),
        compound_lines=[
            "audiocodes_tel2ip_attempted_calls",
        ],
    ),
    upper=graphs.Graph(
        name="ip2tel_attempted_calls",
        title=Title("IP2Tel"),
        compound_lines=[
            "audiocodes_ip2tel_attempted_calls",
        ],
    ),
)
