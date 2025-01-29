#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_emcvnx_targeted_higher = metrics.Metric(
    name="emcvnx_targeted_higher",
    title=Title("Data targeted for higher tier"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_emcvnx_targeted_lower = metrics.Metric(
    name="emcvnx_targeted_lower",
    title=Title("Data targeted for lower tier"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_emcvnx_targeted_within = metrics.Metric(
    name="emcvnx_targeted_within",
    title=Title("Data targeted for within tier"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

graph_emcvnx_storage_pools_targeted = graphs.Graph(
    name="emcvnx_storage_pools_targeted",
    title=Title("EMC VNX storage pools targeted tiers"),
    compound_lines=[
        "emcvnx_targeted_higher",
        "emcvnx_targeted_lower",
        "emcvnx_targeted_within",
    ],
)
