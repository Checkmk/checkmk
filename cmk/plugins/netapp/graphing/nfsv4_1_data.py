#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_nfsv4_1_read_data = metrics.Metric(
    name="nfsv4_1_read_data",
    title=Title("NFSv4.1 data read"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_nfsv4_1_write_data = metrics.Metric(
    name="nfsv4_1_write_data",
    title=Title("NFSv4.1 data written"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_nfsv4_1_traffic = graphs.Bidirectional(
    name="nfsv4_1_traffic",
    title=Title("NFSv4.1 traffic"),
    lower=graphs.Graph(
        name="nfsv4_1_traffic_lower",
        title=Title("NFSv4.1 traffic"),
        compound_lines=["nfsv4_1_read_data"],
    ),
    upper=graphs.Graph(
        name="nfsv4_1_traffic_upper",
        title=Title("NFSv4.1 traffic"),
        compound_lines=["nfsv4_1_write_data"],
    ),
)
