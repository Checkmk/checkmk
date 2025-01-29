#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_bytes_downloaded = metrics.Metric(
    name="bytes_downloaded",
    title=Title("Bytes downloaded"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_bytes_uploaded = metrics.Metric(
    name="bytes_uploaded",
    title=Title("Bytes uploaded"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_data_transfer = graphs.Graph(
    name="data_transfer",
    title=Title("Data transfer"),
    compound_lines=[
        "bytes_downloaded",
        "bytes_uploaded",
    ],
)
