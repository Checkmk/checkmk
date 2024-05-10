#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_bar1_mem_usage_free = metrics.Metric(
    name="bar1_mem_usage_free",
    title=Title("BAR1 memory usage (free)"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_bar1_mem_usage_total = metrics.Metric(
    name="bar1_mem_usage_total",
    title=Title("BAR1 memory usage (total)"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_bar1_mem_usage_used = metrics.Metric(
    name="bar1_mem_usage_used",
    title=Title("BAR1 memory usage (used)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_gpu_utilization = metrics.Metric(
    name="gpu_utilization",
    title=Title("GPU utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
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
metric_decoder_utilization = metrics.Metric(
    name="decoder_utilization",
    title=Title("Decoder utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_encoder_utilization = metrics.Metric(
    name="encoder_utilization",
    title=Title("Encoder utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_gpu_utilization = perfometers.Perfometer(
    name="gpu_utilization",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["gpu_utilization"],
)
perfometer_encoder_utilization_decoder_utilization = perfometers.Bidirectional(
    name="en_decoder_utilization",
    left=perfometers.Perfometer(
        name="encoder_utilization",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["encoder_utilization"],
    ),
    right=perfometers.Perfometer(
        name="decoder_utilization",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["decoder_utilization"],
    ),
)

graph_bar1_mem_usage = graphs.Graph(
    name="bar1_mem_usage",
    title=Title("BAR1 memory usage"),
    compound_lines=[
        "bar1_mem_usage_used",
        "bar1_mem_usage_free",
    ],
    simple_lines=["bar1_mem_usage_total"],
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
