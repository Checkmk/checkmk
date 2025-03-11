#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_SECOND = metrics.Unit(metrics.TimeNotation())

metric_audiocodes_tel2ip_total_duration = metrics.Metric(
    name="audiocodes_tel2ip_total_duration",
    title=Title("Tel2IP Total duration of SIP/H323 calls"),
    unit=UNIT_SECOND,
    color=metrics.Color.GREEN,
)
metric_audiocodes_ip2tel_total_duration = metrics.Metric(
    name="audiocodes_ip2tel_total_duration",
    title=Title("IP2Tel Total duration of SIP/H323 calls"),
    unit=UNIT_SECOND,
    color=metrics.Color.PURPLE,
)
graph_audiocodes_sip_calls_total_duration = graphs.Bidirectional(
    name="audiocodes_sip_calls_total_duration",
    title=Title("Total duration of SIP/H323 calls"),
    lower=graphs.Graph(
        name="tel2ip_total_duration",
        title=Title("Tel2IP"),
        compound_lines=[
            "audiocodes_tel2ip_total_duration",
        ],
    ),
    upper=graphs.Graph(
        name="ip2tel_total_duration",
        title=Title("IP2Tel"),
        compound_lines=[
            "audiocodes_ip2tel_total_duration",
        ],
    ),
)
