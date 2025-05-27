#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    GetRateError,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, int]


def parse_bazel_cache(string_table: StringTable) -> Section:
    return {key: int(float(value)) for key, value in json.loads(string_table[0][0]).items()}


def discover_bazel_cache(section: Section) -> DiscoveryResult:
    yield Service()


def check_bazel_cache_impl(
    section: Section, value_store: MutableMapping[str, Any], current_time: float
) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No Bazel Cache Metrics data")
        return

    yield Result(state=State.OK, summary="Bazel Cache is OK")

    metric_name_prefix = "bazel_cache_metrics_"

    yield from check_levels(
        section["bazel_remote_azblob_cache_hits"],
        metric_name=f"{metric_name_prefix}bazel_remote_azblob_cache_hits",
        render_func=str,
        label="Total number of azblob backend cache hits",
    )
    yield from check_levels(
        section["bazel_remote_azblob_cache_misses"],
        metric_name=f"{metric_name_prefix}bazel_remote_azblob_cache_misses",
        render_func=str,
        label="Total number of azblob backend cache missess",
    )
    yield from check_levels(
        section["bazel_remote_disk_cache_evicted_bytes_total"],
        metric_name=f"{metric_name_prefix}bazel_remote_disk_cache_evicted_bytes_total",
        render_func=render.bytes,
        label="Total number of azblob backend cache missess",
    )
    yield from check_levels(
        section["bazel_remote_disk_cache_logical_bytes"],
        metric_name=f"{metric_name_prefix}bazel_remote_disk_cache_logical_bytes",
        render_func=render.bytes,
        label="Number of bytes in the disk backend if they were uncompressed",
    )
    yield from check_levels(
        section["bazel_remote_disk_cache_longest_item_idle_time_seconds"],
        metric_name=f"{metric_name_prefix}bazel_remote_disk_cache_longest_item_idle_time_seconds",
        render_func=render.timespan,
        label="Idle time of last item in the LRU cache",
    )
    yield from check_levels(
        section["bazel_remote_disk_cache_overwritten_bytes_total"],
        metric_name=f"{metric_name_prefix}bazel_remote_disk_cache_overwritten_bytes_total",
        render_func=render.bytes,
        label="Total number of bytes removed from disk backend",
    )

    try:
        key = "bazel_remote_disk_cache_overwritten_bytes_total"
        read_ops_per_sec = get_rate(value_store, f"last_{key}", current_time, section[key])
        yield from check_levels(
            read_ops_per_sec,
            metric_name=f"{metric_name_prefix}bazel_remote_disk_cache_overwritten_bytes_rate",
            render_func=render.iobandwidth,
            label="Change of the number of bytes removed from disk backend",
        )
    except GetRateError:
        pass

    yield from check_levels(
        section["bazel_remote_disk_cache_size_bytes"],
        metric_name=f"{metric_name_prefix}bazel_remote_disk_cache_size_bytes",
        render_func=render.bytes,
        label="Number of bytes in the disk backend",
    )
    yield from check_levels(
        section["bazel_remote_http_cache_hits"],
        metric_name=f"{metric_name_prefix}bazel_remote_http_cache_hits",
        render_func=str,
        label="Total number of HTTP backend cache hits",
    )
    yield from check_levels(
        section["bazel_remote_http_cache_misses"],
        metric_name=f"{metric_name_prefix}bazel_remote_http_cache_misses",
        render_func=str,
        label="Total number of HTTP backend cache missess",
    )
    yield from check_levels(
        section["bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit"],
        metric_name=f"{metric_name_prefix}bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit",
        render_func=str,
        label="Total number of incoming AC get cache request hits",
    )
    yield from check_levels(
        section["bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss"],
        metric_name=f"{metric_name_prefix}bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss",
        render_func=str,
        label="Total number of incoming AC get cache request misses",
    )
    yield from check_levels(
        section["bazel_remote_s3_cache_hits"],
        metric_name=f"{metric_name_prefix}bazel_remote_s3_cache_hits",
        render_func=render.bytes,
        label="Total number of S3 backend cache hits",
    )
    yield from check_levels(
        section["bazel_remote_s3_cache_misses"],
        metric_name=f"{metric_name_prefix}bazel_remote_s3_cache_misses",
        render_func=str,
        label="Total number of S3 backend cache missess",
    )
    yield from check_levels(
        section["process_cpu_seconds_total"],
        metric_name=f"{metric_name_prefix}process_cpu_seconds_total",
        render_func=render.bytes,
        label="Total user and system CPU time spent in seconds",
    )
    yield from check_levels(
        section["process_max_fds"],
        metric_name=f"{metric_name_prefix}process_max_fds",
        render_func=str,
        label="Maximum number of open file descriptors",
    )
    yield from check_levels(
        section["process_open_fds"],
        metric_name=f"{metric_name_prefix}process_open_fds",
        render_func=str,
        label="Number of open file descriptors",
    )
    yield from check_levels(
        section["process_resident_memory_bytes"],
        metric_name=f"{metric_name_prefix}process_resident_memory_bytes",
        render_func=render.bytes,
        label="Resident memory size",
    )
    yield from check_levels(
        section["process_start_time_seconds"],
        metric_name=f"{metric_name_prefix}process_start_time_seconds",
        render_func=render.datetime,
        label="Start time of the process since unix epoch",
    )
    yield from check_levels(
        section["process_virtual_memory_bytes"],
        metric_name=f"{metric_name_prefix}process_virtual_memory_bytes",
        render_func=render.bytes,
        label="Virtual memory size",
    )
    yield from check_levels(
        section["process_virtual_memory_max_bytes"],
        metric_name=f"{metric_name_prefix}process_virtual_memory_max_bytes",
        render_func=render.bytes,
        label="Maximum amount of virtual memory available",
    )


def check_bazel_cache(section: Section) -> CheckResult:
    yield from check_bazel_cache_impl(section, get_value_store(), time.time())


agent_section_bazel_cache = AgentSection(
    name="bazel_cache_metrics",
    parse_function=parse_bazel_cache,
)

check_plugin_bazel_cache = CheckPlugin(
    name="bazel_cache_metrics",
    service_name="Bazel Cache Metrics",
    discovery_function=discover_bazel_cache,
    check_function=check_bazel_cache,
)
