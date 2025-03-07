#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_cpu_util_guest = metrics.Metric(
    name="cpu_util_guest",
    title=Title("Guest operating systems"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_util_steal = metrics.Metric(
    name="cpu_util_steal",
    title=Title("Steal"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_engine_cpu_util = metrics.Metric(
    name="engine_cpu_util",
    title=Title("Engine CPU utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_idle = metrics.Metric(
    name="idle",
    title=Title("Idle"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_interrupt = metrics.Metric(
    name="interrupt",
    title=Title("Interrupt"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_io_wait = metrics.Metric(
    name="io_wait",
    title=Title("I/O-wait"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_nice = metrics.Metric(
    name="nice",
    title=Title("Nice"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_streams = metrics.Metric(
    name="streams",
    title=Title("Streams"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_system = metrics.Metric(
    name="system",
    title=Title("System"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_user = metrics.Metric(
    name="user",
    title=Title("User"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_util = metrics.Metric(
    name="util",
    title=Title("CPU utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_util_average = metrics.Metric(
    name="util_average",
    title=Title("CPU utilization (average)"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_util_numcpu_as_max = metrics.Metric(
    name="util_numcpu_as_max",
    title=Title("CPU utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_privileged = metrics.Metric(
    name="privileged",
    title=Title("Privileged"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)

perfometer_user_system_idle_nice = perfometers.Perfometer(
    name="user_system_idle_nice",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=[
        "user",
        "system",
        "idle",
        "nice",
    ],
)
perfometer_user_system_idle_io_wait = perfometers.Perfometer(
    name="user_system_idle_io_wait",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=[
        "user",
        "system",
        "idle",
        "io_wait",
    ],
)
perfometer_user_system_io_wait = perfometers.Perfometer(
    name="user_system_io_wait",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=[
        "user",
        "system",
        "io_wait",
    ],
)
perfometer_util = perfometers.Perfometer(
    name="util",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["util"],
)
perfometer_util_numcpu_as_max = perfometers.Perfometer(
    name="util_numcpu_as_max",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["util_numcpu_as_max"],
)
perfometer_user_system_streams = perfometers.Perfometer(
    name="user_system_streams",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=[
        "user",
        "system",
        "streams",
    ],
)

graph_util_average_1 = graphs.Graph(
    name="util_average_1",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["util"],
    simple_lines=[
        "util_average",
        metrics.WarningOf("util"),
        metrics.CriticalOf("util"),
    ],
    conflicting=[
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
        "io_wait",
        "user",
        "system",
    ],
)
graph_cpu_utilization_numcpus = graphs.Graph(
    name="cpu_utilization_numcpus",
    title=Title(
        'CPU utilization (_EXPRESSION:{"metric":"util_numcpu_as_max","scalar":"max"} CPU Threads)'
    ),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "privileged",
    ],
    simple_lines=[
        "util_numcpu_as_max",
        metrics.WarningOf("util_numcpu_as_max"),
        metrics.CriticalOf("util_numcpu_as_max"),
    ],
    optional=[
        "user",
        "privileged",
    ],
)
graph_cpu_utilization_simple = graphs.Graph(
    name="cpu_utilization_simple",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
    ],
    simple_lines=[
        "util_average",
        "util",
    ],
    optional=["util_average"],
    conflicting=[
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
        "io_wait",
    ],
)
graph_cpu_utilization_3 = graphs.Graph(
    name="cpu_utilization_3",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "idle",
        "nice",
    ],
)
graph_cpu_utilization_4 = graphs.Graph(
    name="cpu_utilization_4",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "idle",
        "io_wait",
    ],
)
graph_cpu_utilization_5 = graphs.Graph(
    name="cpu_utilization_5",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
    ],
    simple_lines=[
        "util_average",
        metrics.Sum(
            Title("Total"),
            metrics.Color.GREEN,
            [
                "user",
                "system",
                "io_wait",
            ],
        ),
    ],
    optional=["util_average"],
    conflicting=[
        "util",
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
    ],
)
graph_cpu_utilization_5_util = graphs.Graph(
    name="cpu_utilization_5_util",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
    ],
    simple_lines=[
        "util_average",
        "util",
        metrics.WarningOf("util"),
        metrics.CriticalOf("util"),
    ],
    optional=["util_average"],
    conflicting=[
        "cpu_util_guest",
        "cpu_util_steal",
    ],
)
graph_cpu_utilization_6_steal = graphs.Graph(
    name="cpu_utilization_6_steal",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
        "cpu_util_steal",
    ],
    simple_lines=[
        "util_average",
        metrics.Sum(
            Title("Total"),
            metrics.Color.GREEN,
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
            ],
        ),
    ],
    optional=["util_average"],
    conflicting=[
        "util",
        "cpu_util_guest",
    ],
)
graph_cpu_utilization_6_steal_util = graphs.Graph(
    name="cpu_utilization_6_steal_util",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
        "cpu_util_steal",
    ],
    simple_lines=[
        "util_average",
        "util",
        metrics.WarningOf("util"),
        metrics.CriticalOf("util"),
    ],
    optional=["util_average"],
    conflicting=["cpu_util_guest"],
)
graph_cpu_utilization_6_guest = graphs.Graph(
    name="cpu_utilization_6_guest",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
        "cpu_util_guest",
    ],
    simple_lines=[
        "util_average",
        metrics.Sum(
            Title("Total"),
            metrics.Color.GREEN,
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
            ],
        ),
    ],
    optional=["util_average"],
    conflicting=["util"],
)
graph_cpu_utilization_6_guest_util = graphs.Graph(
    name="cpu_utilization_6_guest_util",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
        "cpu_util_guest",
    ],
    simple_lines=[
        "util_average",
        "util",
        metrics.WarningOf("util"),
        metrics.CriticalOf("util"),
    ],
    optional=["util_average"],
    conflicting=["cpu_util_steal"],
)
graph_cpu_utilization_7 = graphs.Graph(
    name="cpu_utilization_7",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    simple_lines=[
        "util_average",
        metrics.Sum(
            Title("Total"),
            metrics.Color.GREEN,
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "cpu_util_steal",
            ],
        ),
    ],
    optional=["util_average"],
    conflicting=["util"],
)
graph_cpu_utilization_7_util = graphs.Graph(
    name="cpu_utilization_7_util",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "io_wait",
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    simple_lines=[
        "util_average",
        "util",
        metrics.WarningOf("util"),
        metrics.CriticalOf("util"),
    ],
    optional=["util_average"],
)
graph_cpu_utilization_8 = graphs.Graph(
    name="cpu_utilization_8",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=[
        "user",
        "system",
        "interrupt",
    ],
)
graph_util_fallback = graphs.Graph(
    name="util_fallback",
    title=Title("CPU utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["util"],
    simple_lines=[
        metrics.WarningOf("util"),
        metrics.CriticalOf("util"),
    ],
    conflicting=[
        "util_average",
        "system",
        "engine_cpu_util",
    ],
)
graph_cpu_utilization = graphs.Graph(
    name="cpu_utilization",
    title=Title("CPU utilization"),
    simple_lines=[
        "util",
        "engine_cpu_util",
    ],
)
