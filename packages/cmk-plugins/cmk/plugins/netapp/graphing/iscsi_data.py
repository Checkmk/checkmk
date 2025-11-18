#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_iscsi_read_data = metrics.Metric(
    name="iscsi_read_data",
    title=Title("ISCSI data read"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_iscsi_write_data = metrics.Metric(
    name="iscsi_write_data",
    title=Title("ISCSI data written"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_iscsi_traffic = graphs.Bidirectional(
    name="iscsi_traffic",
    title=Title("iSCSI traffic"),
    lower=graphs.Graph(
        name="iscsi_traffic_lower",
        title=Title("iSCSI traffic"),
        compound_lines=["iscsi_read_data"],
    ),
    upper=graphs.Graph(
        name="iscsi_traffic_upper",
        title=Title("iSCSI traffic"),
        compound_lines=["iscsi_write_data"],
    ),
)
