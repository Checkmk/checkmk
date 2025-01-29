#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.plugins.bazel.agent_based.bazel_cache_metrics as bc
from cmk.agent_based.v2 import Metric, Result, Service, State

TEST_TIMEZONE = ZoneInfo("CET")

TEST_TIME_2024 = datetime.datetime(2024, 4, 30, 10, 2, 25, tzinfo=TEST_TIMEZONE)


@pytest.fixture(scope="module", name="section")
def _section() -> bc.Section:
    return bc.parse_bazel_cache(
        [
            [
                '{"bazel_remote_azblob_cache_hits": "0", "bazel_remote_azblob_cache_misses": "0", "bazel_remote_disk_cache_evicted_bytes_total": "0", "bazel_remote_disk_cache_logical_bytes": "6.66901065728e+11", "bazel_remote_disk_cache_longest_item_idle_time_seconds": "5.574440756946148e+06", "bazel_remote_disk_cache_overwritten_bytes_total": "24401", "bazel_remote_disk_cache_size_bytes": "2.8304451584e+11", "bazel_remote_http_cache_hits": "0", "bazel_remote_http_cache_misses": "0", "bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit": "56728", "bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss": "1544", "bazel_remote_incoming_requests_total_kind_cas_method_contains_status_hit": "767062", "bazel_remote_incoming_requests_total_kind_cas_method_contains_status_miss": "234067", "bazel_remote_incoming_requests_total_kind_cas_method_get_status_hit": "6.874294e+06", "bazel_remote_s3_cache_hits": "0", "bazel_remote_s3_cache_misses": "0", "process_cpu_seconds_total": "7810.13", "process_max_fds": "1.048576e+06", "process_open_fds": "12", "process_resident_memory_bytes": "7.968219136e+09", "process_start_time_seconds": "1.71402738122e+09", "process_virtual_memory_bytes": "5.8050449408e+10", "process_virtual_memory_max_bytes": "1.8446744073709552e+19", "promhttp_metric_handler_requests_in_flight": "1", "promhttp_metric_handler_requests_total_code_200": "690", "promhttp_metric_handler_requests_total_code_500": "0", "promhttp_metric_handler_requests_total_code_503": "0"}'
            ]
        ]
    )


def test_discover_bazel_cache(section: bc.Section) -> None:
    assert list(bc.discover_bazel_cache(section)) == [Service()]


def test_check_bazel_cache(section: bc.Section) -> None:
    with time_machine.travel(TEST_TIME_2024):
        assert list(bc.check_bazel_cache(section)) == [
            Result(state=State.OK, summary="Bazel Cache is OK"),
            Result(state=State.OK, summary="Total number of azblob backend cache hits: 0"),
            Metric("bazel_cache_metrics_bazel_remote_azblob_cache_hits", 0.0),
            Result(state=State.OK, summary="Total number of azblob backend cache missess: 0"),
            Metric("bazel_cache_metrics_bazel_remote_azblob_cache_misses", 0.0),
            Result(state=State.OK, summary="Total number of azblob backend cache missess: 0 B"),
            Metric("bazel_cache_metrics_bazel_remote_disk_cache_evicted_bytes_total", 0.0),
            Result(
                state=State.OK,
                summary="Number of bytes in the disk backend if they were uncompressed: 621 GiB",
            ),
            Metric("bazel_cache_metrics_bazel_remote_disk_cache_logical_bytes", 666901065728.0),
            Result(
                state=State.OK, summary="Idle time of last item in the LRU cache: 64 days 12 hours"
            ),
            Metric(
                "bazel_cache_metrics_bazel_remote_disk_cache_longest_item_idle_time_seconds",
                5574440.0,
            ),
            Result(
                state=State.OK, summary="Total number of bytes removed from disk backend: 23.8 KiB"
            ),
            Metric("bazel_cache_metrics_bazel_remote_disk_cache_overwritten_bytes_total", 24401.0),
            Result(state=State.OK, summary="Number of bytes in the disk backend: 264 GiB"),
            Metric("bazel_cache_metrics_bazel_remote_disk_cache_size_bytes", 283044515840.0),
            Result(state=State.OK, summary="Total number of HTTP backend cache hits: 0"),
            Metric("bazel_cache_metrics_bazel_remote_http_cache_hits", 0.0),
            Result(state=State.OK, summary="Total number of HTTP backend cache missess: 0"),
            Metric("bazel_cache_metrics_bazel_remote_http_cache_misses", 0.0),
            Result(
                state=State.OK, summary="Total number of incoming AC get cache request hits: 56728"
            ),
            Metric(
                "bazel_cache_metrics_bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit",
                56728.0,
            ),
            Result(
                state=State.OK, summary="Total number of incoming AC get cache request misses: 1544"
            ),
            Metric(
                "bazel_cache_metrics_bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss",
                1544.0,
            ),
            Result(state=State.OK, summary="Total number of S3 backend cache hits: 0 B"),
            Metric("bazel_cache_metrics_bazel_remote_s3_cache_hits", 0.0),
            Result(state=State.OK, summary="Total number of S3 backend cache missess: 0"),
            Metric("bazel_cache_metrics_bazel_remote_s3_cache_misses", 0.0),
            Result(
                state=State.OK, summary="Total user and system CPU time spent in seconds: 7.63 KiB"
            ),
            Metric("bazel_cache_metrics_process_cpu_seconds_total", 7810.0),
            Result(state=State.OK, summary="Maximum number of open file descriptors: 1048576"),
            Metric("bazel_cache_metrics_process_max_fds", 1048576.0),
            Result(state=State.OK, summary="Number of open file descriptors: 12"),
            Metric("bazel_cache_metrics_process_open_fds", 12.0),
            Result(state=State.OK, summary="Resident memory size: 7.42 GiB"),
            Metric("bazel_cache_metrics_process_resident_memory_bytes", 7968219136.0),
            Result(
                state=State.OK,
                summary="Start time of the process since unix epoch: 2024-04-25 08:43:01",
            ),
            Metric("bazel_cache_metrics_process_start_time_seconds", 1714027381.0),
            Result(state=State.OK, summary="Virtual memory size: 54.1 GiB"),
            Metric("bazel_cache_metrics_process_virtual_memory_bytes", 58050449408.0),
            Result(state=State.OK, summary="Maximum amount of virtual memory available: 16.0 EiB"),
            Metric("bazel_cache_metrics_process_virtual_memory_max_bytes", 1.8446744073709552e19),
        ]
