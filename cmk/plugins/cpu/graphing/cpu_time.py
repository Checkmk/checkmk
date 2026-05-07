#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_children_system_time = metrics.Metric(
    name="children_system_time",
    title=Title("Child time in system space"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_RED,
)
metric_children_user_time = metrics.Metric(
    name="children_user_time",
    title=Title("Child time in user space"),
    unit=UNIT_TIME,
    color=metrics.Color.GRAY,
)
metric_cmk_time_agent = metrics.Metric(
    name="cmk_time_agent",
    title=Title("Time spent waiting for Checkmk agent"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_cmk_time_ds = metrics.Metric(
    name="cmk_time_ds",
    title=Title("Time spent waiting for special agent"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_cmk_time_snmp = metrics.Metric(
    name="cmk_time_snmp",
    title=Title("Time spent waiting for SNMP responses"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
metric_execution_time = metrics.Metric(
    name="execution_time",
    title=Title("Total execution time"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_system_time = metrics.Metric(
    name="system_time",
    title=Title("CPU time in system space"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_user_time = metrics.Metric(
    name="user_time",
    title=Title("CPU time in user space"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_GREEN,
)

perfometer_execution_time = perfometers.Perfometer(
    name="execution_time",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(90.0),
    ),
    segments=["execution_time"],
)

graph_used_cpu_time = graphs.Graph(
    name="used_cpu_time",
    title=Title("Used CPU Time"),
    compound_lines=[
        "user_time",
        "children_user_time",
        "system_time",
        "children_system_time",
    ],
    simple_lines=[
        metrics.Sum(
            Title("Total"),
            metrics.Color.DARK_BLUE,
            [
                "user_time",
                "children_user_time",
                "system_time",
                "children_system_time",
            ],
        )
    ],
    conflicting=[
        "cmk_time_agent",
        "cmk_time_snmp",
        "cmk_time_ds",
    ],
)
graph_cmk_cpu_time_by_phase = graphs.Graph(
    name="cmk_cpu_time_by_phase",
    title=Title("Time usage by phase"),
    compound_lines=[
        metrics.Sum(
            Title("CPU time in user space"),
            metrics.Color.PINK,
            [
                "user_time",
                "children_user_time",
            ],
        ),
        metrics.Sum(
            Title("CPU time in operating system"),
            metrics.Color.DARK_BLUE,
            [
                "system_time",
                "children_system_time",
            ],
        ),
        "cmk_time_agent",
        "cmk_time_snmp",
        "cmk_time_ds",
    ],
    simple_lines=["execution_time"],
    optional=[
        "cmk_time_agent",
        "cmk_time_snmp",
        "cmk_time_ds",
    ],
)
graph_cpu_time = graphs.Graph(
    name="cpu_time",
    title=Title("CPU Time"),
    compound_lines=[
        "user_time",
        "system_time",
    ],
    simple_lines=[
        metrics.Sum(
            Title("Total"),
            metrics.Color.GRAY,
            [
                "user_time",
                "system_time",
            ],
        )
    ],
    conflicting=["children_user_time"],
)
