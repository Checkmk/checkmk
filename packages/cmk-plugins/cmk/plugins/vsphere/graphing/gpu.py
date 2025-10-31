#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_esx_gpu_utilization = metrics.Metric(
    name="esx_gpu_utilization",
    title=Title("GPU Utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

perfometer_esx_gpu_utilization = perfometers.Perfometer(
    name="esx_gpu_utilization",
    focus_range=perfometers.FocusRange(
        lower=perfometers.Closed(0),
        upper=perfometers.Open(100),
    ),
    segments=["esx_gpu_utilization"],
)

graph_esx_gpu_utilization = graphs.Graph(
    name="esx_gpu_utilization",
    title=Title("GPU Utilization"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=("esx_gpu_utilization",),
    simple_lines=(
        metrics.WarningOf("esx_gpu_utilization"),
        metrics.CriticalOf("esx_gpu_utilization"),
    ),
)
