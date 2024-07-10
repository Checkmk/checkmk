#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_if_in_errors = metrics.Metric(
    name="if_in_errors",
    title=Title("Input errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_if_in_discards = metrics.Metric(
    name="if_in_discards",
    title=Title("Input discards"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_if_out_errors = metrics.Metric(
    name="if_out_errors",
    title=Title("Output errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_if_out_discards = metrics.Metric(
    name="if_out_discards",
    title=Title("Output discards"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

graph_if_errors_discards = graphs.Bidirectional(
    name="if_errors_discards",
    title=Title("Errors"),
    lower=graphs.Graph(
        name="if_errors_out",
        title=Title("Errors"),
        compound_lines=[
            "if_out_errors",
            "if_out_discards",
        ],
    ),
    upper=graphs.Graph(
        name="if_errors_in",
        title=Title("Errors"),
        compound_lines=[
            "if_in_errors",
            "if_in_discards",
        ],
    ),
)
