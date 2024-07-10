#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

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
metric_max_file_descriptors = metrics.Metric(
    name="max_file_descriptors",
    title=Title("Max file descriptors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_number_of_in_flight_fetch = metrics.Metric(
    name="number_of_in_flight_fetch",
    title=Title("Ongoing shard info requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
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
metric_open_file_descriptors = metrics.Metric(
    name="open_file_descriptors",
    title=Title("Open file descriptors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_task_max_waiting_in_queue_millis = metrics.Metric(
    name="task_max_waiting_in_queue_millis",
    title=Title("Maximum wait time of all tasks in queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
