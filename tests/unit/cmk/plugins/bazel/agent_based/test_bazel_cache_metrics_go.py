#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.plugins.bazel.agent_based.bazel_cache_metrics_go as bcmg
from cmk.agent_based.v2 import Metric, Result, Service, State

TEST_TIMEZONE = ZoneInfo("CET")

TEST_TIME_2024 = datetime.datetime(2024, 4, 30, 10, 2, 25, tzinfo=TEST_TIMEZONE)


@pytest.fixture(scope="module", name="section")
def _section() -> bcmg.Section:
    return bcmg.parse_bazel_cache_go(
        [
            [
                '{"go_gc_duration_seconds_count": "241", "go_gc_duration_seconds_quantile_0": "2.556e-05", "go_gc_duration_seconds_quantile_0_25": "0.000118884", "go_gc_duration_seconds_quantile_0_5": "0.000279329", "go_gc_duration_seconds_quantile_0_75": "0.000566935", "go_gc_duration_seconds_quantile_1": "0.006215666", "go_gc_duration_seconds_sum": "0.109311885", "go_goroutines": "13", "go_info": "1", "go_memstats_alloc_bytes": "6.017385136e+09", "go_memstats_alloc_bytes_total": "1.069483667848e+12", "go_memstats_buck_hash_sys_bytes": "2.157607e+06", "go_memstats_frees_total": "8.230473771e+09", "go_memstats_gc_sys_bytes": "1.13489564e+09", "go_memstats_heap_alloc_bytes": "6.017385136e+09", "go_memstats_heap_idle_bytes": "4.5727956992e+10", "go_memstats_heap_inuse_bytes": "6.433456128e+09", "go_memstats_heap_objects": "8.2156623e+07", "go_memstats_heap_released_bytes": "4.5536632832e+10", "go_memstats_heap_sys_bytes": "5.216141312e+10", "go_memstats_last_gc_time_seconds": "1.7140514771001196e+09", "go_memstats_lookups_total": "0", "go_memstats_mallocs_total": "8.312630394e+09", "go_memstats_mcache_inuse_bytes": "4800", "go_memstats_mcache_sys_bytes": "15600", "go_memstats_mspan_inuse_bytes": "9.93192e+07", "go_memstats_mspan_sys_bytes": "2.249712e+08", "go_memstats_next_gc_bytes": "1.1127494592e+10", "go_memstats_other_sys_bytes": "2.0319041e+07", "go_memstats_stack_inuse_bytes": "7.20896e+06", "go_memstats_stack_sys_bytes": "7.20896e+06", "go_memstats_sys_bytes": "5.3550981168e+10", "go_threads": "205"}'
            ]
        ]
    )


def test_discover_bazel_cache(section: bcmg.Section) -> None:
    assert list(bcmg.discover_bazel_cache(section)) == [Service()]


def test_check_bazel_cache_go(section: bcmg.Section) -> None:
    with time_machine.travel(TEST_TIME_2024):
        assert list(bcmg.check_bazel_cache_go(section)) == [
            Result(state=State.OK, summary="Bazel Cache Go is OK"),
            Result(
                state=State.OK,
                summary="Timespan since last Go garbage collection cycle: 4 minutes 1 second",
            ),
            Metric("bazel_cache_go_go_gc_duration_seconds_count", 241.0),
            Result(state=State.OK, summary="Number of goroutines: 13"),
            Metric("bazel_cache_go_go_goroutines", 13.0),
            Result(state=State.OK, summary="Bytes allocated and in use: 5.60 GiB"),
            Metric("bazel_cache_go_go_memstats_alloc_bytes", 6017385136.0),
            Result(state=State.OK, summary="Bytes used by profiling bucket hash table: 2.06 MiB"),
            Metric("bazel_cache_go_go_memstats_buck_hash_sys_bytes", 2157607.0),
            Result(
                state=State.OK,
                summary="Bytes used for garbage collection system metadata: 1.06 GiB",
            ),
            Metric("bazel_cache_go_go_memstats_gc_sys_bytes", 1134895640.0),
            Result(state=State.OK, summary="Heap bytes allocated and in use: 5.60 GiB"),
            Metric("bazel_cache_go_go_memstats_heap_alloc_bytes", 6017385136.0),
            Result(state=State.OK, summary="Heap bytes waiting to be used: 42.6 GiB"),
            Metric("bazel_cache_go_go_memstats_heap_idle_bytes", 45727956992.0),
            Result(state=State.OK, summary="Heap bytes released to OS: 42.4 GiB"),
            Metric("bazel_cache_go_go_memstats_heap_released_bytes", 45536632832.0),
            Result(state=State.OK, summary="Time since last garbage collection: 4 days 18 hours"),
            Metric("bazel_cache_go_go_memstats_last_gc_time_seconds", 412668.0),
            Result(
                state=State.OK,
                summary="Heap bytes when next garbage collection will take place: 10.4 GiB",
            ),
            Metric("bazel_cache_go_go_memstats_next_gc_bytes", 11127494592.0),
            Result(state=State.OK, summary="Bytes used for other system allocations: 19.4 MiB"),
            Metric("bazel_cache_go_go_memstats_other_sys_bytes", 20319041.0),
            Result(state=State.OK, summary="Bytes in use by stack allocator: 6.88 MiB"),
            Metric("bazel_cache_go_go_memstats_stack_inuse_bytes", 7208960.0),
            Result(
                state=State.OK, summary="Bytes obtained from system for stack allocator: 6.88 MiB"
            ),
            Metric("bazel_cache_go_go_memstats_stack_sys_bytes", 7208960.0),
            Result(state=State.OK, summary="Bytes obtained from system: 49.9 GiB"),
            Metric("bazel_cache_go_go_memstats_sys_bytes", 53550981168.0),
            Result(state=State.OK, summary="Number of OS threads created: 205 B"),
            Metric("bazel_cache_go_go_threads", 205.0),
        ]
