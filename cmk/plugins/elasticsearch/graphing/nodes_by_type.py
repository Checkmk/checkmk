#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_number_of_nodes = metrics.Metric(
    name="number_of_nodes",
    title=Title("Nodes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_number_of_data_nodes = metrics.Metric(
    name="number_of_data_nodes",
    title=Title("Data nodes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

graph_nodes_by_type = graphs.Graph(
    name="nodes_by_type",
    title=Title("Running nodes by nodes type"),
    compound_lines=["number_of_nodes"],
    simple_lines=["number_of_data_nodes"],
)
