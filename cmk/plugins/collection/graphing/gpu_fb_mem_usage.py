#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_fb_mem_usage_free = metrics.Metric(
    name="fb_mem_usage_free",
    title=Title("FB memory usage (free)"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_fb_mem_usage_total = metrics.Metric(
    name="fb_mem_usage_total",
    title=Title("FB memory usage (total)"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_fb_mem_usage_used = metrics.Metric(
    name="fb_mem_usage_used",
    title=Title("FB memory usage (used)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

graph_fb_mem_usage = graphs.Graph(
    name="fb_mem_usage",
    title=Title("FB memory usage"),
    compound_lines=[
        "fb_mem_usage_used",
        "fb_mem_usage_free",
    ],
    simple_lines=["fb_mem_usage_total"],
)
