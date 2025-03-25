#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_oracle_sga_size = metrics.Metric(
    name="oracle_sga_size",
    title=Title("Oracle maximum SGA size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GRAY,
)
metric_oracle_pga_total_pga_allocated = metrics.Metric(
    name="oracle_pga_total_pga_allocated",
    title=Title("Oracle total PGA allocated"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_oracle_pga_total_pga_inuse = metrics.Metric(
    name="oracle_pga_total_pga_inuse",
    title=Title("Oracle total PGA inuse"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_oracle_pga_total_freeable_pga_memory = metrics.Metric(
    name="oracle_pga_total_freeable_pga_memory",
    title=Title("Oracle total freeable PGA memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_oracle_sga_buffer_cache = metrics.Metric(
    name="oracle_sga_buffer_cache",
    title=Title("Oracle buffer cache size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_oracle_sga_java_pool = metrics.Metric(
    name="oracle_sga_java_pool",
    title=Title("Oracle Java pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_oracle_sga_large_pool = metrics.Metric(
    name="oracle_sga_large_pool",
    title=Title("Oracle large pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.PINK,
)
metric_oracle_sga_redo_buffer = metrics.Metric(
    name="oracle_sga_redo_buffer",
    title=Title("Oracle redo buffers"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_oracle_sga_shared_io_pool = metrics.Metric(
    name="oracle_sga_shared_io_pool",
    title=Title("Oracle shared IO pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_sga_shared_pool = metrics.Metric(
    name="oracle_sga_shared_pool",
    title=Title("Oracle shared pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_sga_streams_pool = metrics.Metric(
    name="oracle_sga_streams_pool",
    title=Title("Oracle streams pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)


perfometer_oracle_sga_pga_size = perfometers.Perfometer(
    name="oracle_sga_pga_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(30000000000),
    ),
    segments=[
        "oracle_sga_size",
        "oracle_pga_total_pga_allocated",
    ],
)

graph_oracle_sga_pga_total = graphs.Graph(
    name="oracle_sga_pga_total",
    title=Title("Oracle memory"),
    compound_lines=[
        "oracle_sga_size",
        "oracle_pga_total_pga_allocated",
    ],
    simple_lines=[
        metrics.Sum(
            Title("Oracle total Memory"),
            metrics.Color.GRAY,
            [
                "oracle_sga_size",
                "oracle_pga_total_pga_allocated",
            ],
        )
    ],
)
graph_oracle_sga_info = graphs.Graph(
    name="oracle_sga_info",
    title=Title("Oracle SGA memory statistics"),
    compound_lines=[
        "oracle_sga_buffer_cache",
        "oracle_sga_shared_pool",
        "oracle_sga_shared_io_pool",
        "oracle_sga_redo_buffer",
        "oracle_sga_java_pool",
        "oracle_sga_large_pool",
        "oracle_sga_streams_pool",
    ],
    simple_lines=["oracle_sga_size"],
    optional=[
        "oracle_sga_java_pool",
        "oracle_sga_large_pool",
        "oracle_sga_streams_pool",
    ],
)
graph_oracle_pga_memory_info = graphs.Graph(
    name="oracle_pga_memory_info",
    title=Title("Oracle PGA memory statistics"),
    simple_lines=[
        "oracle_pga_total_pga_allocated",
        "oracle_pga_total_pga_inuse",
        "oracle_pga_total_freeable_pga_memory",
    ],
    optional=["oracle_pga_total_freeable_pga_memory"],
)
