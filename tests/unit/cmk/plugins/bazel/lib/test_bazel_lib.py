#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from unittest import mock

import pytest

from cmk.plugins.bazel.lib.agent import agent_bazel_cache_main, parse_arguments

METRICS_RESPONSE = """# HELP bazel_remote_azblob_cache_hits The total number of azblob backend cache hits
# TYPE bazel_remote_azblob_cache_hits counter
bazel_remote_azblob_cache_hits 0
# HELP bazel_remote_azblob_cache_misses The total number of azblob backend cache misses
# TYPE bazel_remote_azblob_cache_misses counter
bazel_remote_azblob_cache_misses 0
# HELP bazel_remote_disk_cache_evicted_bytes_total The total number of bytes evicted from disk backend, due to full cache
# TYPE bazel_remote_disk_cache_evicted_bytes_total counter
bazel_remote_disk_cache_evicted_bytes_total 0
# HELP bazel_remote_disk_cache_logical_bytes The current number of bytes in the disk backend if they were uncompressed
# TYPE bazel_remote_disk_cache_logical_bytes gauge
bazel_remote_disk_cache_logical_bytes 2.6872918016e+11
# HELP bazel_remote_disk_cache_longest_item_idle_time_seconds The idle time (now - atime) of the last item in the LRU cache, updated once per minute. Depending on filesystem mount options (e.g. relatime), the resolution may be measured in 'days' and not accurate to the second. If using noatime this will be 0.
# TYPE bazel_remote_disk_cache_longest_item_idle_time_seconds gauge
bazel_remote_disk_cache_longest_item_idle_time_seconds 1.257133290844899e+06
# HELP bazel_remote_disk_cache_overwritten_bytes_total The total number of bytes removed from disk backend, due to put of already existing key
# TYPE bazel_remote_disk_cache_overwritten_bytes_total counter
bazel_remote_disk_cache_overwritten_bytes_total 140096
# HELP bazel_remote_disk_cache_size_bytes The current number of bytes in the disk backend
# TYPE bazel_remote_disk_cache_size_bytes gauge
bazel_remote_disk_cache_size_bytes 1.1447904256e+11
# HELP bazel_remote_http_cache_hits The total number of HTTP backend cache hits
# TYPE bazel_remote_http_cache_hits counter
bazel_remote_http_cache_hits 0
# HELP bazel_remote_http_cache_misses The total number of HTTP backend cache misses
# TYPE bazel_remote_http_cache_misses counter
bazel_remote_http_cache_misses 0
# HELP bazel_remote_incoming_requests_total The number of incoming cache requests
# TYPE bazel_remote_incoming_requests_total counter
bazel_remote_incoming_requests_total{kind="ac",method="get",status="hit"} 119882
bazel_remote_incoming_requests_total{kind="ac",method="get",status="miss"} 6960
# HELP bazel_remote_s3_cache_hits The total number of s3 backend cache hits
# TYPE bazel_remote_s3_cache_hits counter
bazel_remote_s3_cache_hits 0
# HELP bazel_remote_s3_cache_misses The total number of s3 backend cache misses
# TYPE bazel_remote_s3_cache_misses counter
bazel_remote_s3_cache_misses 0
# HELP go_gc_duration_seconds A summary of the pause duration of garbage collection cycles.
# TYPE go_gc_duration_seconds summary
go_gc_duration_seconds{quantile="0"} 9.4473e-05
go_gc_duration_seconds{quantile="0.25"} 0.000274378
go_gc_duration_seconds{quantile="0.5"} 0.000487193
go_gc_duration_seconds{quantile="0.75"} 0.000784432
go_gc_duration_seconds{quantile="1"} 0.005608786
go_gc_duration_seconds_sum 0.803301822
go_gc_duration_seconds_count 968
# HELP go_goroutines Number of goroutines that currently exist.
# TYPE go_goroutines gauge
go_goroutines 76
# HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
# TYPE go_memstats_alloc_bytes gauge
go_memstats_alloc_bytes 4.45263448e+09
# HELP go_memstats_buck_hash_sys_bytes Number of bytes used by the profiling bucket hash table.
# TYPE go_memstats_buck_hash_sys_bytes gauge
go_memstats_buck_hash_sys_bytes 2.336119e+06
# HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
# TYPE go_memstats_gc_sys_bytes gauge
go_memstats_gc_sys_bytes 7.12454592e+08
# HELP go_memstats_heap_alloc_bytes Number of heap bytes allocated and still in use.
# TYPE go_memstats_heap_alloc_bytes gauge
go_memstats_heap_alloc_bytes 4.45263448e+09
# HELP go_memstats_heap_idle_bytes Number of heap bytes waiting to be used.
# TYPE go_memstats_heap_idle_bytes gauge
go_memstats_heap_idle_bytes 3.135340544e+10
# HELP go_memstats_heap_objects Number of allocated objects.
# TYPE go_memstats_heap_objects gauge
go_memstats_heap_objects 2.866946e+07
# HELP go_memstats_heap_released_bytes Number of heap bytes released to OS.
# TYPE go_memstats_heap_released_bytes gauge
go_memstats_heap_released_bytes 3.0019944448e+10
# HELP go_memstats_last_gc_time_seconds Number of seconds since 1970 of last garbage collection.
# TYPE go_memstats_last_gc_time_seconds gauge
go_memstats_last_gc_time_seconds 1.7097342808446639e+09
# HELP go_memstats_next_gc_bytes Number of heap bytes when next garbage collection will take place.
# TYPE go_memstats_next_gc_bytes gauge
go_memstats_next_gc_bytes 8.80778356e+09
# HELP go_memstats_other_sys_bytes Number of bytes used for other system allocations.
# TYPE go_memstats_other_sys_bytes gauge
go_memstats_other_sys_bytes 1.0149457e+07
# HELP go_memstats_stack_inuse_bytes Number of bytes in use by the stack allocator.
# TYPE go_memstats_stack_inuse_bytes gauge
go_memstats_stack_inuse_bytes 1.2189696e+07
# HELP go_memstats_stack_sys_bytes Number of bytes obtained from system for stack allocator.
# TYPE go_memstats_stack_sys_bytes gauge
go_memstats_stack_sys_bytes 1.2189696e+07
# HELP go_memstats_sys_bytes Number of bytes obtained from system.
# TYPE go_memstats_sys_bytes gauge
go_memstats_sys_bytes 3.6876329464e+10
# HELP go_threads Number of OS threads created.
# TYPE go_threads gauge
go_threads 302
# HELP grpc_server_handled_total Total number of RPCs completed on the server, regardless of success or failure.
# TYPE grpc_server_handled_total counter
grpc_server_handled_total{grpc_code="NotFound",grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 6960
grpc_server_handled_total{grpc_code="NotFound",grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream"} 52
grpc_server_handled_total{grpc_code="OK",grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 7081
grpc_server_handled_total{grpc_code="OK",grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 119882
grpc_server_handled_total{grpc_code="OK",grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary"} 4244
grpc_server_handled_total{grpc_code="OK",grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary"} 1264
grpc_server_handled_total{grpc_code="OK",grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream"} 1.5902261e+07
grpc_server_handled_total{grpc_code="OK",grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 7049
grpc_server_handled_total{grpc_code="OK",grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream"} 369674
# HELP grpc_server_handling_seconds Histogram of response latency (seconds) of gRPC that had been application-level handled by the server.
# TYPE grpc_server_handling_seconds histogram
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="0.5"} 7030
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="+Inf"} 7081
grpc_server_handling_seconds_sum{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 90.8053342549999
grpc_server_handling_seconds_count{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 7081
# HELP http_request_duration_seconds The latency of the HTTP requests.
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="0.5"} 961
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="+Inf"} 972
http_request_duration_seconds_sum{code="200",handler="metrics",method="GET",service=""} 20.28851677500002
http_request_duration_seconds_count{code="200",handler="metrics",method="GET",service=""} 972
# HELP http_requests_inflight The number of inflight requests being handled at the same time.
# TYPE http_requests_inflight gauge
http_requests_inflight{handler="GET",service=""} 0
http_requests_inflight{handler="HEAD",service=""} 0
http_requests_inflight{handler="KDFARY",service=""} 0
http_requests_inflight{handler="NESSUS",service=""} 0
http_requests_inflight{handler="OPTIONS",service=""} 0
http_requests_inflight{handler="POST",service=""} 0
http_requests_inflight{handler="PROPFIND",service=""} 0
http_requests_inflight{handler="SEARCH",service=""} 0
http_requests_inflight{handler="TRACE",service=""} 0
http_requests_inflight{handler="TRACK",service=""} 0
http_requests_inflight{handler="metrics",service=""} 1
# HELP http_response_size_bytes The size of the HTTP responses.
# TYPE http_response_size_bytes histogram
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="100"} 0
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="+Inf"} 972
http_response_size_bytes_sum{code="200",handler="metrics",method="GET",service=""} 4.4765e+06
http_response_size_bytes_count{code="200",handler="metrics",method="GET",service=""} 972
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 17190.38
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 1.048576e+06
# HELP process_open_fds Number of open file descriptors.
# TYPE process_open_fds gauge
process_open_fds 32
# HELP process_resident_memory_bytes Resident memory size in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 6.821412864e+09
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 1.70967396224e+09
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 4.2206461952e+10
# HELP process_virtual_memory_max_bytes Maximum amount of virtual memory available in bytes.
# TYPE process_virtual_memory_max_bytes gauge
process_virtual_memory_max_bytes 1.8446744073709552e+19
"""

STATUS_RESPONSE = {
    "CurrSize": 283741868032,
    "UncompressedSize": 668958797824,
    "ReservedSize": 0,
    "MaxSize": 483183820800,
    "NumFiles": 15967454,
    "ServerTime": 1714376779,
    "GitCommit": "c5bf6e13938aa89923c637b5a4f01c2203a3c9f8",
    "NumGoroutines": 9,
}


class MockResponse:
    text = METRICS_RESPONSE
    status_code = 200
    content = "non-empty"

    @staticmethod
    def json() -> dict[str, object]:
        return STATUS_RESPONSE


def test_parse_minimal_arguments() -> None:
    args = parse_arguments(["--host", "bazel-cache.tld"])
    assert args.host == "bazel-cache.tld"
    assert args.port == 8080
    assert args.protocol == "https"
    assert not args.no_cert_check


def test_parse_all_arguments() -> None:
    args = parse_arguments(
        [
            "--user",
            "harry",
            "--password",
            "hirsch",
            "--host",
            "bazel-cache.tld",
            "--port",
            "8081",
            "--protocol",
            "http",
            "--no-cert-check",
        ]
    )
    assert args.user == "harry"
    assert args.password == "hirsch"
    assert args.host == "bazel-cache.tld"
    assert args.port == 8081
    assert args.protocol == "http"
    assert args.no_cert_check


@mock.patch(
    "cmk.plugins.bazel.lib.agent.requests.get",
    mock.Mock(return_value=MockResponse),
)
def test_bazel_cache_agent_output_has_bazel_cache_status_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    arg_list = [
        "--host",
        "bazel-cache.tld",
    ]
    args = parse_arguments(arg_list)
    agent_bazel_cache_main(args=args)
    captured = capsys.readouterr()
    output = captured.out.rstrip().split("\n")
    assert "<<<bazel_cache_status:sep(0)>>>" in output
    index = output.index("<<<bazel_cache_status:sep(0)>>>") + 1
    data = json.loads(output[index])

    assert data["curr_size"] == 283741868032
    assert data["git_commit"] == "c5bf6e13938aa89923c637b5a4f01c2203a3c9f8"
    assert data["num_files"] == 15967454
    assert data["num_goroutines"] == 9
    assert data["reserved_size"] == 0
    assert data["server_time"] == 1714376779
    assert data["uncompressed_size"] == 668958797824


@mock.patch(
    "cmk.plugins.bazel.lib.agent.requests.get",
    mock.Mock(return_value=MockResponse),
)
def test_bazel_cache_agent_output_has_bazel_cache_metrics_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    arg_list = [
        "--host",
        "bazel-cache.tld",
    ]
    args = parse_arguments(arg_list)
    agent_bazel_cache_main(args=args)
    captured = capsys.readouterr()

    output = captured.out.rstrip().split("\n")
    assert "<<<bazel_cache_metrics:sep(0)>>>" in output
    index = output.index("<<<bazel_cache_metrics:sep(0)>>>") + 1
    data = json.loads(output[index])
    assert data["bazel_remote_azblob_cache_hits"] == "0"
    assert data["bazel_remote_azblob_cache_misses"] == "0"
    assert data["bazel_remote_disk_cache_evicted_bytes_total"] == "0"
    assert data["bazel_remote_disk_cache_logical_bytes"] == "2.6872918016e+11"
    assert data["bazel_remote_disk_cache_longest_item_idle_time_seconds"] == "1.257133290844899e+06"
    assert data["bazel_remote_disk_cache_overwritten_bytes_total"] == "140096"
    assert data["bazel_remote_disk_cache_size_bytes"] == "1.1447904256e+11"
    assert data["bazel_remote_http_cache_hits"] == "0"
    assert data["bazel_remote_http_cache_misses"] == "0"
    assert data["bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit"] == "119882"
    assert data["bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss"] == "6960"
    assert data["bazel_remote_s3_cache_hits"] == "0"
    assert data["bazel_remote_s3_cache_misses"] == "0"
    assert data["process_cpu_seconds_total"] == "17190.38"
    assert data["process_max_fds"] == "1.048576e+06"
    assert data["process_open_fds"] == "32"
    assert data["process_resident_memory_bytes"] == "6.821412864e+09"
    assert data["process_start_time_seconds"] == "1.70967396224e+09"
    assert data["process_virtual_memory_bytes"] == "4.2206461952e+10"
    assert data["process_virtual_memory_max_bytes"] == "1.8446744073709552e+19"


#
@mock.patch(
    "cmk.plugins.bazel.lib.agent.requests.get",
    mock.Mock(return_value=MockResponse),
)
def test_bazel_cache_agent_output_has_bazel_cache_metrics_go_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    arg_list = [
        "--host",
        "bazel-cache.tld",
    ]
    args = parse_arguments(arg_list)
    agent_bazel_cache_main(args=args)
    captured = capsys.readouterr()

    output = captured.out.rstrip().split("\n")
    assert "<<<bazel_cache_metrics_go:sep(0)>>>" in output
    index = output.index("<<<bazel_cache_metrics_go:sep(0)>>>") + 1
    data = json.loads(output[index])
    assert data["go_gc_duration_seconds_count"] == "968"
    assert data["go_gc_duration_seconds_quantile_0"] == "9.4473e-05"
    assert data["go_gc_duration_seconds_quantile_0_25"] == "0.000274378"
    assert data["go_gc_duration_seconds_quantile_0_5"] == "0.000487193"
    assert data["go_gc_duration_seconds_quantile_0_75"] == "0.000784432"
    assert data["go_gc_duration_seconds_quantile_1"] == "0.005608786"
    assert data["go_gc_duration_seconds_sum"] == "0.803301822"
    assert data["go_goroutines"] == "76"
    assert data["go_memstats_alloc_bytes"] == "4.45263448e+09"
    assert data["go_memstats_buck_hash_sys_bytes"] == "2.336119e+06"
    assert data["go_memstats_gc_sys_bytes"] == "7.12454592e+08"
    assert data["go_memstats_heap_alloc_bytes"] == "4.45263448e+09"
    assert data["go_memstats_heap_idle_bytes"] == "3.135340544e+10"
    assert data["go_memstats_heap_objects"] == "2.866946e+07"
    assert data["go_memstats_heap_released_bytes"] == "3.0019944448e+10"
    assert data["go_memstats_last_gc_time_seconds"] == "1.7097342808446639e+09"
    assert data["go_memstats_next_gc_bytes"] == "8.80778356e+09"
    assert data["go_memstats_other_sys_bytes"] == "1.0149457e+07"
    assert data["go_memstats_stack_inuse_bytes"] == "1.2189696e+07"
    assert data["go_memstats_stack_sys_bytes"] == "1.2189696e+07"
    assert data["go_memstats_sys_bytes"] == "3.6876329464e+10"
    assert data["go_threads"] == "302"


#
@mock.patch(
    "cmk.plugins.bazel.lib.agent.requests.get",
    mock.Mock(return_value=MockResponse),
)
def test_bazel_cache_agent_output_has_bazel_cache_metrics_grpc_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    arg_list = [
        "--host",
        "bazel-cache.tld",
    ]
    args = parse_arguments(arg_list)

    agent_bazel_cache_main(args=args)
    captured = capsys.readouterr()
    output = captured.out.rstrip().split("\n")
    assert "<<<bazel_cache_metrics_grpc:sep(0)>>>" in output
    index = output.index("<<<bazel_cache_metrics_grpc:sep(0)>>>") + 1
    data = json.loads(output[index])
    assert (
        data[
            "grpc_server_handled_total_grpc_code_NotFound_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary"
        ]
        == "6960"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_NotFound_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream"
        ]
        == "52"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_OK_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary"
        ]
        == "7081"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_OK_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary"
        ]
        == "119882"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_OK_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary"
        ]
        == "4244"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_OK_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary"
        ]
        == "1264"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_OK_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream"
        ]
        == "1.5902261e+07"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_OK_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary"
        ]
        == "7049"
    )
    assert (
        data[
            "grpc_server_handled_total_grpc_code_OK_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream"
        ]
        == "369674"
    )
    assert (
        data[
            "grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_+Inf"
        ]
        == "7081"
    )
    assert (
        data[
            "grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_0_5"
        ]
        == "7030"
    )
    assert (
        data[
            "grpc_server_handling_seconds_count_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary"
        ]
        == "7081"
    )
    assert (
        data[
            "grpc_server_handling_seconds_sum_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary"
        ]
        == "90.8053342549999"
    )


@mock.patch(
    "cmk.plugins.bazel.lib.agent.requests.get",
    mock.Mock(return_value=MockResponse),
)
def test_bazel_cache_agent_output_has_bazel_cache_metrics_http(
    capsys: pytest.CaptureFixture[str],
) -> None:
    arg_list = [
        "--host",
        "bazel-cache.tld",
    ]
    args = parse_arguments(arg_list)

    agent_bazel_cache_main(args=args)
    captured = capsys.readouterr()

    output = captured.out.rstrip().split("\n")
    assert "<<<bazel_cache_metrics_http:sep(0)>>>" in output
    index = output.index("<<<bazel_cache_metrics_http:sep(0)>>>") + 1
    data = json.loads(output[index])

    assert (
        data["http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_+Inf"]
        == "972"
    )
    assert (
        data["http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_0_5"]
        == "961"
    )
    assert data["http_request_duration_seconds_count_code_200_handler_metrics_method_GET"] == "972"
    assert (
        data["http_request_duration_seconds_sum_code_200_handler_metrics_method_GET"]
        == "20.28851677500002"
    )
    assert data["http_requests_inflight_handler_GET"] == "0"
    assert data["http_requests_inflight_handler_HEAD"] == "0"
    assert data["http_requests_inflight_handler_KDFARY"] == "0"
    assert data["http_requests_inflight_handler_NESSUS"] == "0"
    assert data["http_requests_inflight_handler_OPTIONS"] == "0"
    assert data["http_requests_inflight_handler_POST"] == "0"
    assert data["http_requests_inflight_handler_PROPFIND"] == "0"
    assert data["http_requests_inflight_handler_SEARCH"] == "0"
    assert data["http_requests_inflight_handler_TRACE"] == "0"
    assert data["http_requests_inflight_handler_TRACK"] == "0"
    assert data["http_requests_inflight_handler_metrics"] == "1"
    assert (
        data["http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_+Inf"] == "972"
    )
    assert data["http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_100"] == "0"
    assert data["http_response_size_bytes_count_code_200_handler_metrics_method_GET"] == "972"
    assert data["http_response_size_bytes_sum_code_200_handler_metrics_method_GET"] == "4.4765e+06"
