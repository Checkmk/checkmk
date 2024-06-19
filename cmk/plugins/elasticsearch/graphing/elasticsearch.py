#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_active_primary_shards = metrics.Metric(
    name="active_primary_shards",
    title=Title("Active primary shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_active_shards = metrics.Metric(
    name="active_shards",
    title=Title("Active shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_active_shards_percent_as_number = metrics.Metric(
    name="active_shards_percent_as_number",
    title=Title("Active shards in percent"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_avg_flush_time = metrics.Metric(
    name="avg_flush_time",
    title=Title("Average flush time"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_delayed_unassigned_shards = metrics.Metric(
    name="delayed_unassigned_shards",
    title=Title("Delayed unassigned shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_elasticsearch_count = metrics.Metric(
    name="elasticsearch_count",
    title=Title("Total documents"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_elasticsearch_count_avg = metrics.Metric(
    name="elasticsearch_count_avg",
    title=Title("Average document count growth"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_elasticsearch_count_rate = metrics.Metric(
    name="elasticsearch_count_rate",
    title=Title("Document count growth per minute"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_elasticsearch_size = metrics.Metric(
    name="elasticsearch_size",
    title=Title("Total size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_CYAN,
)
metric_elasticsearch_size_avg = metrics.Metric(
    name="elasticsearch_size_avg",
    title=Title("Average size growth"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_elasticsearch_size_rate = metrics.Metric(
    name="elasticsearch_size_rate",
    title=Title("Size growth per minute"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_file_descriptors_open_attempts = metrics.Metric(
    name="file_descriptors_open_attempts",
    title=Title("File descriptor open attempts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_file_descriptors_open_attempts_rate = metrics.Metric(
    name="file_descriptors_open_attempts_rate",
    title=Title("File descriptor open attempts rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_flush_time = metrics.Metric(
    name="flush_time",
    title=Title("Flush time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_flushed = metrics.Metric(
    name="flushed",
    title=Title("Flushes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_initializing_shards = metrics.Metric(
    name="initializing_shards",
    title=Title("Initializing shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)
metric_max_file_descriptors = metrics.Metric(
    name="max_file_descriptors",
    title=Title("Max file descriptors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_number_of_data_nodes = metrics.Metric(
    name="number_of_data_nodes",
    title=Title("Data nodes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_number_of_in_flight_fetch = metrics.Metric(
    name="number_of_in_flight_fetch",
    title=Title("Ongoing shard info requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_number_of_nodes = metrics.Metric(
    name="number_of_nodes",
    title=Title("Nodes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_number_of_pending_tasks = metrics.Metric(
    name="number_of_pending_tasks",
    title=Title("Pending tasks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BROWN,
)
metric_number_of_pending_tasks_avg = metrics.Metric(
    name="number_of_pending_tasks_avg",
    title=Title("Average pending tasks delta"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_number_of_pending_tasks_rate = metrics.Metric(
    name="number_of_pending_tasks_rate",
    title=Title("Pending tasks delta"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_open_file_descriptors = metrics.Metric(
    name="open_file_descriptors",
    title=Title("Open file descriptors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_relocating_shards = metrics.Metric(
    name="relocating_shards",
    title=Title("Relocating shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_task_max_waiting_in_queue_millis = metrics.Metric(
    name="task_max_waiting_in_queue_millis",
    title=Title("Maximum wait time of all tasks in queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_unassigned_shards = metrics.Metric(
    name="unassigned_shards",
    title=Title("Unassigned shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

perfometer_number_of_pending_tasks_rate = perfometers.Perfometer(
    name="number_of_pending_tasks_rate",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20),
    ),
    segments=["number_of_pending_tasks_rate"],
)
perfometer_active_shards_percent_as_number = perfometers.Perfometer(
    name="active_shards_percent_as_number",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["active_shards_percent_as_number"],
)
perfometer_active_shards = perfometers.Bidirectional(
    name="active_shards",
    left=perfometers.Perfometer(
        name="active_primary_shards",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed("active_shards"),
        ),
        segments=["active_primary_shards"],
    ),
    right=perfometers.Perfometer(
        name="active_shards",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed("active_shards"),
        ),
        segments=["active_shards"],
    ),
)
perfometer_elasticsearch_rate = perfometers.Stacked(
    name="elasticsearch_rate",
    lower=perfometers.Perfometer(
        name="elasticsearch_count_rate",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(20),
        ),
        segments=["elasticsearch_count_rate"],
    ),
    upper=perfometers.Perfometer(
        name="elasticsearch_size_rate",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(9000),
        ),
        segments=["elasticsearch_size_rate"],
    ),
)

graph_shards_allocation = graphs.Graph(
    name="shards_allocation",
    title=Title("Shard allocation over time"),
    simple_lines=[
        "active_shards",
        "active_primary_shards",
        "relocating_shards",
        "initializing_shards",
        "unassigned_shards",
    ],
)
graph_active_shards = graphs.Graph(
    name="active_shards",
    title=Title("Active shards"),
    simple_lines=[
        "active_shards",
        "active_primary_shards",
    ],
)
graph_nodes_by_type = graphs.Graph(
    name="nodes_by_type",
    title=Title("Running nodes by nodes type"),
    compound_lines=["number_of_nodes"],
    simple_lines=["number_of_data_nodes"],
)
