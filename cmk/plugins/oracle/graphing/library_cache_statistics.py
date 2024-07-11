#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_pin_hits_sum = metrics.Metric(
    name="oracle_pin_hits_sum",
    title=Title("Oracle pin hits sum"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_pins_sum = metrics.Metric(
    name="oracle_pins_sum",
    title=Title("Oracle pins sum"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_oracle_library_cache_statistics = graphs.Graph(
    name="oracle_library_cache_statistics",
    title=Title("Oracle library cache statistics"),
    simple_lines=[
        "oracle_pins_sum",
        "oracle_pin_hits_sum",
    ],
)
