#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_fcp_read_data = metrics.Metric(
    name="fcp_read_data",
    title=Title("FCP data read"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_fcp_write_data = metrics.Metric(
    name="fcp_write_data",
    title=Title("FCP data written"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_fcp_traffic = graphs.Bidirectional(
    name="fcp_traffic",
    title=Title("FCP traffic"),
    lower=graphs.Graph(
        name="fcp_traffic_lower",
        title=Title("FCP traffic"),
        compound_lines=["fcp_read_data"],
    ),
    upper=graphs.Graph(
        name="fcp_traffic_upper",
        title=Title("FCP traffic"),
        compound_lines=["fcp_write_data"],
    ),
)
