#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_xmpp_failed_inbound_streams = metrics.Metric(
    name="xmpp_failed_inbound_streams",
    title=Title("XmppFederationProxy - Failed inbound stream establishes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_xmpp_failed_outbound_streams = metrics.Metric(
    name="xmpp_failed_outbound_streams",
    title=Title("XmppFederationProxy - Failed outbound stream establishes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_streams_streams = graphs.Bidirectional(
    name="streams_streams",
    title=Title("Streams"),
    lower=graphs.Graph(
        name="streams",
        title=Title("Streams"),
        compound_lines=["xmpp_failed_outbound_streams"],
    ),
    upper=graphs.Graph(
        name="streams",
        title=Title("Streams"),
        compound_lines=["xmpp_failed_inbound_streams"],
    ),
)
