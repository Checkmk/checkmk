#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_iscsi_read_ops = metrics.Metric(
    name="iscsi_read_ops",
    title=Title("ISCSI read ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_iscsi_write_ops = metrics.Metric(
    name="iscsi_write_ops",
    title=Title("ISCSI write ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_iscsi_ops = graphs.Bidirectional(
    name="iscsi_ops",
    title=Title("iSCSI operations"),
    lower=graphs.Graph(
        name="iscsi_ops_lower",
        title=Title("iSCSI operations"),
        compound_lines=["iscsi_read_ops"],
    ),
    upper=graphs.Graph(
        name="iscsi_ops_upper",
        title=Title("iSCSI operations"),
        compound_lines=["iscsi_write_ops"],
    ),
)
