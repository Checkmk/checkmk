#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_HZ = metrics.Unit(metrics.IECNotation("Hz"))

metric_graphics_clock = metrics.Metric(
    name="graphics_clock",
    title=Title("Graphics Clock speed"),
    unit=UNIT_HZ,
    color=metrics.Color.GREEN,
)
metric_graphics_clock_max = metrics.Metric(
    name="graphics_clock_max",
    title=Title("Graphics Clock speed (Max)"),
    unit=UNIT_HZ,
    color=metrics.Color.PURPLE,
)

graph_graphics_clock = graphs.Graph(
    name="graphics_clock",
    title=Title("Graphics Clock speed"),
    simple_lines=["graphics_clock", "graphics_clock_max"],
)

metric_sm_clock = metrics.Metric(
    name="sm_clock",
    title=Title("SM Clock speed"),
    unit=UNIT_HZ,
    color=metrics.Color.GREEN,
)
metric_sm_clock_max = metrics.Metric(
    name="sm_clock_max",
    title=Title("SM Clock speed (Max)"),
    unit=UNIT_HZ,
    color=metrics.Color.PURPLE,
)

graph_sm_clock = graphs.Graph(
    name="sm_clock",
    title=Title("SM Clock speed"),
    simple_lines=["sm_clock", "sm_clock_max"],
)

metric_mem_clock = metrics.Metric(
    name="mem_clock",
    title=Title("MEM Clock speed"),
    unit=UNIT_HZ,
    color=metrics.Color.GREEN,
)
metric_mem_clock_max = metrics.Metric(
    name="mem_clock_max",
    title=Title("MEM Clock speed (Max)"),
    unit=UNIT_HZ,
    color=metrics.Color.PURPLE,
)

graph_mem_clock = graphs.Graph(
    name="mem_clock",
    title=Title("MEM Clock speed"),
    simple_lines=["mem_clock", "mem_clock_max"],
)

metric_video_clock = metrics.Metric(
    name="video_clock",
    title=Title("Video Clock speed"),
    unit=UNIT_HZ,
    color=metrics.Color.GREEN,
)
metric_video_clock_max = metrics.Metric(
    name="video_clock_max",
    title=Title("Video Clock speed (Max)"),
    unit=UNIT_HZ,
    color=metrics.Color.PURPLE,
)

graph_video_clock = graphs.Graph(
    name="video_clock",
    title=Title("Video Clock speed"),
    simple_lines=["video_clock", "video_clock_max"],
)
