#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_index_count = metrics.Metric(
    name="index_count",
    title=Title("Indices"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_num_collections = metrics.Metric(
    name="num_collections",
    title=Title("Collections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_num_extents = metrics.Metric(
    name="num_extents",
    title=Title("Extents"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_num_input = metrics.Metric(
    name="num_input",
    title=Title("Inputs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_num_output = metrics.Metric(
    name="num_output",
    title=Title("Outputs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_num_stream_rule = metrics.Metric(
    name="num_stream_rule",
    title=Title("Stream rules"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_num_extractor = metrics.Metric(
    name="num_extractor",
    title=Title("Extractors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_num_streams = metrics.Metric(
    name="num_streams",
    title=Title("Number of streams"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_collectors_running = metrics.Metric(
    name="collectors_running",
    title=Title("Running collectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_collectors_stopped = metrics.Metric(
    name="collectors_stopped",
    title=Title("Stopped collectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_collectors_failing = metrics.Metric(
    name="collectors_failing",
    title=Title("Failing collectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_num_objects = metrics.Metric(
    name="num_objects",
    title=Title("Objects"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_store_size = metrics.Metric(
    name="store_size",
    title=Title("Store size"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_id_cache_size = metrics.Metric(
    name="id_cache_size",
    title=Title("ID cache size"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_field_data_size = metrics.Metric(
    name="field_data_size",
    title=Title("Field data size"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_avg_doc_size = metrics.Metric(
    name="avg_doc_size",
    title=Title("Average document size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_YELLOW,
)
