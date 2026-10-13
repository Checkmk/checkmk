#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_page_swap_out = metrics.Metric(
    name="page_swap_out",
    title=Title("Page swap out"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_page_swap_in = metrics.Metric(
    name="page_swap_in",
    title=Title("Page swap in"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_page_swap_in_out = graphs.Bidirectional(
    name="page_swap_in_out",
    title=Title("Page swap"),
    lower=graphs.Graph(
        name="page_swap_out",
        title=Title("Page swap out"),
        compound_lines=["page_swap_out"],
    ),
    upper=graphs.Graph(
        name="page_swap_in",
        title=Title("Page swap in"),
        compound_lines=["page_swap_in"],
    ),
)
