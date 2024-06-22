#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from datetime import timedelta
from time import time

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, int]


def parse_bazel_cache_go(string_table: StringTable) -> Section:
    return {key: int(float(value)) for key, value in json.loads(string_table[0][0]).items()}


def discover_bazel_cache(section: Section) -> DiscoveryResult:
    yield Service()


def check_bazel_cache_go(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No Bazel Cache Go data")
        return

    yield Result(state=State.OK, summary="Bazel Cache Go is OK")

    metric_name_prefix = "bazel_cache_go_"

    yield from check_levels(
        section["go_gc_duration_seconds_count"],
        metric_name=f"{metric_name_prefix}go_gc_duration_seconds_count",
        render_func=render.timespan,
        label="Timespan since last Go garbage collection cycle",
    )
    yield from check_levels(
        section["go_goroutines"],
        metric_name=f"{metric_name_prefix}go_goroutines",
        render_func=str,
        label="Number of goroutines",
    )
    yield from check_levels(
        section["go_memstats_alloc_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_alloc_bytes",
        render_func=render.bytes,
        label="Bytes allocated and in use",
    )
    yield from check_levels(
        section["go_memstats_buck_hash_sys_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_buck_hash_sys_bytes",
        render_func=render.bytes,
        label="Bytes used by profiling bucket hash table",
    )
    yield from check_levels(
        section["go_memstats_gc_sys_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_gc_sys_bytes",
        render_func=render.bytes,
        label="Bytes used for garbage collection system metadata",
    )
    yield from check_levels(
        section["go_memstats_heap_alloc_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_heap_alloc_bytes",
        render_func=render.bytes,
        label="Heap bytes allocated and in use",
    )
    yield from check_levels(
        section["go_memstats_heap_idle_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_heap_idle_bytes",
        render_func=render.bytes,
        label="Heap bytes waiting to be used",
    )
    yield from check_levels(
        section["go_memstats_heap_released_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_heap_released_bytes",
        render_func=render.bytes,
        label="Heap bytes released to OS",
    )
    yield from check_levels(
        timedelta(
            seconds=(time() - int(section["go_memstats_last_gc_time_seconds"]))
        ).total_seconds(),
        metric_name=f"{metric_name_prefix}go_memstats_last_gc_time_seconds",
        render_func=render.timespan,
        label="Time since last garbage collection",
    )
    yield from check_levels(
        section["go_memstats_next_gc_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_next_gc_bytes",
        render_func=render.bytes,
        label="Heap bytes when next garbage collection will take place",
    )
    yield from check_levels(
        section["go_memstats_other_sys_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_other_sys_bytes",
        render_func=render.bytes,
        label="Bytes used for other system allocations",
    )
    yield from check_levels(
        section["go_memstats_stack_inuse_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_stack_inuse_bytes",
        render_func=render.bytes,
        label="Bytes in use by stack allocator",
    )
    yield from check_levels(
        section["go_memstats_stack_sys_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_stack_sys_bytes",
        render_func=render.bytes,
        label="Bytes obtained from system for stack allocator",
    )
    yield from check_levels(
        section["go_memstats_sys_bytes"],
        metric_name=f"{metric_name_prefix}go_memstats_sys_bytes",
        render_func=render.bytes,
        label="Bytes obtained from system",
    )
    yield from check_levels(
        section["go_threads"],
        metric_name=f"{metric_name_prefix}go_threads",
        render_func=render.bytes,
        label="Number of OS threads created",
    )


agent_section_bazel_cache = AgentSection(
    name="bazel_cache_metrics_go",
    parse_function=parse_bazel_cache_go,
)

check_plugin_bazel_cache_go = CheckPlugin(
    name="bazel_cache_metrics_go",
    service_name="Bazel Cache Metrics Go",
    discovery_function=discover_bazel_cache,
    check_function=check_bazel_cache_go,
)
