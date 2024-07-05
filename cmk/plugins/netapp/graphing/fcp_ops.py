#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_fcp_read_ops = metrics.Metric(
    name="fcp_read_ops",
    title=Title("FCP read ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_fcp_write_ops = metrics.Metric(
    name="fcp_write_ops",
    title=Title("FCP write ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_fcp_ops = graphs.Bidirectional(
    name="fcp_ops",
    title=Title("FCP operations"),
    lower=graphs.Graph(
        name="fcp_ops_lower",
        title=Title("FCP operations"),
        compound_lines=["fcp_read_ops"],
    ),
    upper=graphs.Graph(
        name="fcp_ops_upper",
        title=Title("FCP operations"),
        compound_lines=["fcp_write_ops"],
    ),
)
