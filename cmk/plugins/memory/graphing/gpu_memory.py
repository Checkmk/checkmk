#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"), metrics.StrictPrecision(2))

metric_gpuactive = metrics.Metric(
    name="gpuactive",
    title=Title("RAM for active GPU objects"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_gpureclaim = metrics.Metric(
    name="gpureclaim",
    title=Title("Reclaimable RAM in GPU pools"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_YELLOW,
)

graph_gpu_memory = graphs.Graph(
    name="gpu_memory",
    title=Title("RAM used by GPU drivers"),
    # GPUReclaim is not counted in GPUActive, so the two add up to the total
    compound_lines=[
        "gpuactive",
        "gpureclaim",
    ],
    simple_lines=[
        metrics.Sum(
            Title("Total RAM used by GPU drivers"),
            metrics.Color.DARK_YELLOW,
            ["gpuactive", "gpureclaim"],
        ),
    ],
)
