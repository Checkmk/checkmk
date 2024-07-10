#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_esi_errors_rate = metrics.Metric(
    name="varnish_esi_errors_rate",
    title=Title("ESI Errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_esi_warnings_rate = metrics.Metric(
    name="varnish_esi_warnings_rate",
    title=Title("ESI Warnings"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_varnish_esi_errors_and_warnings = graphs.Graph(
    name="varnish_esi_errors_and_warnings",
    title=Title("Varnish ESI Errors and Warnings"),
    simple_lines=[
        "varnish_esi_errors_rate",
        "varnish_esi_warnings_rate",
    ],
)
