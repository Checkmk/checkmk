#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_emcvnx_move_down = metrics.Metric(
    name="emcvnx_move_down",
    title=Title("Data to move down"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_emcvnx_move_up = metrics.Metric(
    name="emcvnx_move_up",
    title=Title("Data to move up"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_emcvnx_move_within = metrics.Metric(
    name="emcvnx_move_within",
    title=Title("Data to move within"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

graph_emcvnx_storage_pools_movement = graphs.Graph(
    name="emcvnx_storage_pools_movement",
    title=Title("EMC VNX storage pools movement"),
    compound_lines=[
        "emcvnx_move_up",
        "emcvnx_move_down",
        "emcvnx_move_within",
    ],
)
