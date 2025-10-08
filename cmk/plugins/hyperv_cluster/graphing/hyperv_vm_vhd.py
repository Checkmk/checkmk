#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, Title
from cmk.graphing.v1.metrics import (
    Color,
    IECNotation,
    Metric,
    StrictPrecision,
    Unit,
)

BYTES_UNIT = Unit(IECNotation("B"), StrictPrecision(2))

prefix = "hyperv_vhd_metrics_"

metric_hyperv_vhd_disk_size = Metric(
    name=f"{prefix}disk_size",
    title=Title("Maximum disk size"),
    unit=BYTES_UNIT,
    color=Color.DARK_BLUE,
)

metric_hyperv_vhd_file_size = Metric(
    name=f"{prefix}file_size",
    title=Title("Current disk size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)

graph_hyperv_vhd = graphs.Graph(
    name=f"{prefix}vhd_graph",
    title=Title("Disk Metrics"),
    compound_lines=(f"{prefix}file_size",),
    simple_lines=(f"{prefix}disk_size",),
)
