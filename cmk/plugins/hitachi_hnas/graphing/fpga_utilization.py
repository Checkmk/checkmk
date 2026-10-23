#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_fpga_util = metrics.Metric(
    name="fpga_util",
    title=Title("FPGA utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_fpga_util = perfometers.Perfometer(
    name="fpga_util",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["fpga_util"],
)

graph_fgpa_utilization = graphs.Graph(
    name="fgpa_utilization",
    title=Title("FGPA utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["fpga_util"],
    simple_lines=[
        metrics.WarningOf("fpga_util"),
        metrics.CriticalOf("fpga_util"),
    ],
)
