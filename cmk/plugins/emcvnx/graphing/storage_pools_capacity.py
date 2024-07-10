#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_emcvnx_consumed_capacity = metrics.Metric(
    name="emcvnx_consumed_capacity",
    title=Title("Consumed capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_emcvnx_avail_capacity = metrics.Metric(
    name="emcvnx_avail_capacity",
    title=Title("Available capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

perfometer_emcvnx_consumed_capacity = perfometers.Perfometer(
    name="emcvnx_consumed_capacity",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(40000000000000),
    ),
    segments=["emcvnx_consumed_capacity"],
)

graph_emcvnx_storage_pools_capacity = graphs.Graph(
    name="emcvnx_storage_pools_capacity",
    title=Title("EMC VNX storage pools capacity"),
    compound_lines=[
        "emcvnx_consumed_capacity",
        "emcvnx_avail_capacity",
    ],
)
