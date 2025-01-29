#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_active = metrics.Metric(
    name="mem_lnx_active",
    title=Title("Active"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_active_anon = metrics.Metric(
    name="mem_lnx_active_anon",
    title=Title("Active (anonymous)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_active_file = metrics.Metric(
    name="mem_lnx_active_file",
    title=Title("Active (files)"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_inactive = metrics.Metric(
    name="mem_lnx_inactive",
    title=Title("Inactive"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_inactive_anon = metrics.Metric(
    name="mem_lnx_inactive_anon",
    title=Title("Inactive (anonymous)"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_mem_lnx_inactive_file = metrics.Metric(
    name="mem_lnx_inactive_file",
    title=Title("Inactive (files)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)

graph_active_and_inactive_memory_anon = graphs.Graph(
    name="active_and_inactive_memory_anon",
    title=Title("Active and inactive memory"),
    compound_lines=[
        "mem_lnx_inactive_anon",
        "mem_lnx_inactive_file",
        "mem_lnx_active_anon",
        "mem_lnx_active_file",
    ],
)
graph_active_and_inactive_memory = graphs.Graph(
    name="active_and_inactive_memory",
    title=Title("Active and inactive memory"),
    compound_lines=[
        "mem_lnx_active",
        "mem_lnx_inactive",
    ],
    conflicting=["mem_lnx_active_anon"],
)
