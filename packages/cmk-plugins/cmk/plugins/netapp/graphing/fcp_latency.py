#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_fcp_read_latency = metrics.Metric(
    name="fcp_read_latency",
    title=Title("FCP read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_fcp_write_latency = metrics.Metric(
    name="fcp_write_latency",
    title=Title("FCP write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_fcp_latency = graphs.Bidirectional(
    name="fcp_latency",
    title=Title("FCP latency"),
    lower=graphs.Graph(
        name="fcp_latency_lower",
        title=Title("FCP latency"),
        compound_lines=["fcp_read_latency"],
    ),
    upper=graphs.Graph(
        name="fcp_latency_upper",
        title=Title("FCP latency"),
        compound_lines=["fcp_write_latency"],
    ),
)
