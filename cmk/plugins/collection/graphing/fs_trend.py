#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_DAY = metrics.Unit(metrics.IECNotation("B/d"))

metric_fs_trend = metrics.Metric(
    name="fs_trend",
    title=Title("Growth trend"),
    unit=UNIT_BYTES_PER_DAY,
    color=metrics.Color.DARK_GRAY,
)

graph_fs_trend = graphs.Graph(
    name="fs_trend",
    title=Title("Growth trend"),
    simple_lines=["fs_trend"],
)
