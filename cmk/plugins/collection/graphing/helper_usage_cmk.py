#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_helper_usage_cmk = metrics.Metric(
    name="helper_usage_cmk",
    title=Title("Checkmk helper usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

graph_helper_usage_cmk = graphs.Graph(
    name="helper_usage_cmk",
    title=Title("Checkmk helper usage"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["helper_usage_cmk"],
)
