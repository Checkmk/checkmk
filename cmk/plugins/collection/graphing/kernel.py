#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_process_creations = metrics.Metric(
    name="process_creations",
    title=Title("Process creations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_context_switches = metrics.Metric(
    name="context_switches",
    title=Title("Context switches"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_major_page_faults = metrics.Metric(
    name="major_page_faults",
    title=Title("Major page faults"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

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

perfometer_major_page_faults = perfometers.Perfometer(
    name="major_page_faults",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(2000)),
    segments=["major_page_faults"],
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
