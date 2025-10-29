#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_cifs_read_ops = metrics.Metric(
    name="cifs_read_ops",
    title=Title("CIFS read ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_cifs_write_ops = metrics.Metric(
    name="cifs_write_ops",
    title=Title("CIFS write ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_cifs_ops = graphs.Bidirectional(
    name="cifs_ops",
    title=Title("CIFS operations"),
    lower=graphs.Graph(
        name="cifs_ops_lower",
        title=Title("CIFS operations"),
        compound_lines=["cifs_read_ops"],
    ),
    upper=graphs.Graph(
        name="cifs_ops_upper",
        title=Title("CIFS operations"),
        compound_lines=["cifs_write_ops"],
    ),
)
