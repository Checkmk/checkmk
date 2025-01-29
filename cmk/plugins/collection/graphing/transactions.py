#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_transactions = metrics.Metric(
    name="transactions",
    title=Title("Transaction count"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_transactions = graphs.Graph(
    name="transactions",
    title=Title("Transactions"),
    simple_lines=["transactions"],
)
