#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_storage_processor_util = metrics.Metric(
    name="storage_processor_util",
    title=Title("Storage processor utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_storage_processor_util = perfometers.Perfometer(
    name="storage_processor_util",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["storage_processor_util"],
)

graph_storage_processor_utilization = graphs.Graph(
    name="storage_processor_utilization",
    title=Title("Storage Processor utilization"),
    compound_lines=["storage_processor_util"],
    simple_lines=[
        metrics.WarningOf("storage_processor_util"),
        metrics.CriticalOf("storage_processor_util"),
    ],
)
