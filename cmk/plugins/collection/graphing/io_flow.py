#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_egress = metrics.Metric(
    name="egress",
    title=Title("Data egress"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_ingress = metrics.Metric(
    name="ingress",
    title=Title("Data ingress"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

perfometer_ingress_egress = perfometers.Bidirectional(
    name="ingress_egress",
    left=perfometers.Perfometer(
        name="ingress",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(2000000000),
        ),
        segments=["ingress"],
    ),
    right=perfometers.Perfometer(
        name="egress",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(2000000000),
        ),
        segments=["egress"],
    ),
)

graph_io_flow = graphs.Bidirectional(
    name="io_flow",
    title=Title("IO flow"),
    lower=graphs.Graph(
        name="io_flow_lower",
        title=Title("IO flow"),
        compound_lines=["egress"],
    ),
    upper=graphs.Graph(
        name="io_flow_upper",
        title=Title("IO flow"),
        compound_lines=["ingress"],
    ),
)
