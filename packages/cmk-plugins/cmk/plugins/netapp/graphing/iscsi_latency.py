#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_iscsi_read_latency = metrics.Metric(
    name="iscsi_read_latency",
    title=Title("ISCSI read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_iscsi_write_latency = metrics.Metric(
    name="iscsi_write_latency",
    title=Title("ISCSI write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_iscsi_latency = graphs.Bidirectional(
    name="iscsi_latency",
    title=Title("iSCSI latency"),
    lower=graphs.Graph(
        name="iscsi_latency_lower",
        title=Title("iSCSI latency"),
        compound_lines=["iscsi_read_latency"],
    ),
    upper=graphs.Graph(
        name="iscsi_latency_upper",
        title=Title("iSCSI latency"),
        compound_lines=["iscsi_write_latency"],
    ),
)
