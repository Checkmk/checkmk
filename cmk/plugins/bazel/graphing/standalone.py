#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import (
    AutoPrecision,
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    TimeNotation,
    Unit,
)

COUNT_UNIT = Unit(DecimalNotation(""), StrictPrecision(0))
BYTES_UNIT = Unit(IECNotation("B"), StrictPrecision(2))
TIME_SINCE_BUILD_UNIT = Unit(TimeNotation(), AutoPrecision(0))

name_prefix_bazel_cache_status = "bazel_cache_status_"
name_prefix_bazel_cache_metrics = "bazel_cache_metrics_"
name_prefix_bazel_cache_go = "bazel_cache_go_"

metric_bazel_curr_size = Metric(
    name=f"{name_prefix_bazel_cache_status}curr_size",
    title=Title("Current size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_bazel_max_size = Metric(
    name=f"{name_prefix_bazel_cache_status}max_size",
    title=Title("Maximum size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_bazel_num_files = Metric(
    name=f"{name_prefix_bazel_cache_status}num_files",
    title=Title("Number of files"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_bazel_num_goroutines = Metric(
    name=f"{name_prefix_bazel_cache_status}num_goroutines",
    title=Title("Number of Go routines"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_bazel_reserved_size = Metric(
    name=f"{name_prefix_bazel_cache_status}reserved_size",
    title=Title("Reserved size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_bazel_uncompressed_size = Metric(
    name=f"{name_prefix_bazel_cache_status}uncompressed_size",
    title=Title("Uncompressed size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)

metric_bazel_remote_azblob_cache_hits = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_azblob_cache_hits",
    title=Title("azblob backend cache hits"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_azblob_cache_misses = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_azblob_cache_misses",
    title=Title("azblob backend cache missess"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_disk_cache_evicted_bytes_total = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_disk_cache_evicted_bytes_total",
    title=Title("Disk backend bytes evicted (full cache)"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_disk_cache_logical_bytes = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_disk_cache_logical_bytes",
    title=Title("Disk backend uncompressed"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_disk_cache_longest_item_idle_time_seconds = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_disk_cache_longest_item_idle_time_seconds",
    title=Title("Idle time of last item in the LRU cache"),
    unit=TIME_SINCE_BUILD_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_disk_cache_overwritten_bytes_total = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_disk_cache_overwritten_bytes_total",
    title=Title("Disk backend bytes removed or overwritten"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)

metric_bazel_remote_disk_cache_overwritten_bytes_rate = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_disk_cache_overwritten_bytes_rate",
    title=Title("Rate of disk backend bytes removed or overwritten"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)

metric_bazel_remote_disk_cache_size_bytes = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_disk_cache_size_bytes",
    title=Title("Disk backend size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_http_cache_hits = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_http_cache_hits",
    title=Title("HTTP backend cache hits"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_http_cache_misses = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_http_cache_misses",
    title=Title("HTTP backend cache missess"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_s3_cache_hits = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_s3_cache_hits",
    title=Title("S3 backend cache hits"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_bazel_remote_s3_cache_misses = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_s3_cache_misses",
    title=Title("S3 backend cache missess"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_process_cpu_seconds_total = Metric(
    name=f"{name_prefix_bazel_cache_metrics}process_cpu_seconds_total",
    title=Title("Total user and system CPU time"),
    unit=TIME_SINCE_BUILD_UNIT,
    color=Color.PURPLE,
)
metric_process_max_fds = Metric(
    name=f"{name_prefix_bazel_cache_metrics}process_max_fds",
    title=Title("Maximum number of open file descriptors"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_process_open_fds = Metric(
    name=f"{name_prefix_bazel_cache_metrics}process_open_fds",
    title=Title("Number of open file descriptors"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_process_resident_memory_bytes = Metric(
    name=f"{name_prefix_bazel_cache_metrics}process_resident_memory_bytes",
    title=Title("Resident memory size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_process_start_time_seconds = Metric(
    name=f"{name_prefix_bazel_cache_metrics}process_start_time_seconds",
    title=Title("Start time of process"),
    unit=TIME_SINCE_BUILD_UNIT,
    color=Color.PURPLE,
)
metric_process_virtual_memory_bytes = Metric(
    name=f"{name_prefix_bazel_cache_metrics}process_virtual_memory_bytes",
    title=Title("Virtual memory size"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_process_virtual_memory_max_bytes = Metric(
    name=f"{name_prefix_bazel_cache_metrics}process_virtual_memory_max_bytes",
    title=Title("Maximum virtual memory available"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)

metric_go_gc_duration_seconds_count = Metric(
    name=f"{name_prefix_bazel_cache_go}go_gc_duration_seconds_count",
    title=Title("Timespan since last Go garbage collection cycle"),
    unit=TIME_SINCE_BUILD_UNIT,
    color=Color.PURPLE,
)
metric_go_goroutines = Metric(
    name=f"{name_prefix_bazel_cache_go}go_goroutines",
    title=Title("Number of goroutines"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_alloc_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_alloc_bytes",
    title=Title("Bytes allocated and in use"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_buck_hash_sys_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_buck_hash_sys_bytes",
    title=Title("Bytes used by profiling bucket hash table"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_gc_sys_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_gc_sys_bytes",
    title=Title("Bytes used for garbage collection system metadata"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_heap_alloc_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_heap_alloc_bytes",
    title=Title("Heap bytes allocated and in use"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_heap_idle_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_heap_idle_bytes",
    title=Title("Heap bytes waiting to be used"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_heap_released_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_heap_released_bytes",
    title=Title("Heap bytes released to OS"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_last_gc_time_seconds = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_last_gc_time_seconds",
    title=Title("Time since last garbage collection"),
    unit=TIME_SINCE_BUILD_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_next_gc_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_next_gc_bytes",
    title=Title("Heap bytes when next garbage collection will take place"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)

metric_go_memstats_other_sys_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_other_sys_bytes",
    title=Title("Bytes used for other system allocations"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_stack_inuse_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_stack_inuse_bytes",
    title=Title("Bytes in use by stack allocator"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_stack_sys_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_stack_sys_bytes",
    title=Title("Bytes obtained from system for stack allocator"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_memstats_sys_bytes = Metric(
    name=f"{name_prefix_bazel_cache_go}go_memstats_sys_bytes",
    title=Title("Bytes obtained from system"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)
metric_go_threads = Metric(
    name=f"{name_prefix_bazel_cache_go}go_threads",
    title=Title("Number of OS threads created"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)
