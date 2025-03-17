#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_physical_reads = metrics.Metric(
    name="oracle_physical_reads",
    title=Title("Oracle physical reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_physical_writes = metrics.Metric(
    name="oracle_physical_writes",
    title=Title("Oracle physical writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_oracle_physical_io_oracle_physical_io = graphs.Bidirectional(
    name="oracle_physical_io",
    title=Title("Oracle physical IO"),
    lower=graphs.Graph(
        name="oracle_physical_writes",
        title=Title("Oracle physical IO"),
        compound_lines=["oracle_physical_writes"],
    ),
    upper=graphs.Graph(
        name="oracle_physical_reads",
        title=Title("Oracle physical IO reads"),
        compound_lines=["oracle_physical_reads"],
    ),
)
