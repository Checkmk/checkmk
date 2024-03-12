#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
bazel_remote_incoming_requests_total{kind="cas",method="contains",status="hit"} 1.185848e+06
bazel_remote_incoming_requests_total{kind="cas",method="contains",status="miss"} 740637
bazel_remote_incoming_requests_total{kind="cas",method="get",status="hit"} 1.5902261e+07
bazel_remote_incoming_requests_total{kind="cas",method="get",status="miss"} 52
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
# HELP go_info Information about the Go environment.
# TYPE go_info gauge
go_info{version="go1.20.1 X:nocoverageredesign"} 1
# HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
# TYPE go_memstats_alloc_bytes gauge
go_memstats_alloc_bytes 4.45263448e+09
# HELP go_memstats_alloc_bytes_total Total number of bytes allocated, even if freed.
# TYPE go_memstats_alloc_bytes_total counter
go_memstats_alloc_bytes_total 2.979080746328e+12
# HELP go_memstats_buck_hash_sys_bytes Number of bytes used by the profiling bucket hash table.
# TYPE go_memstats_buck_hash_sys_bytes gauge
go_memstats_buck_hash_sys_bytes 2.336119e+06
# HELP go_memstats_frees_total Total number of frees.
# TYPE go_memstats_frees_total counter
go_memstats_frees_total 1.8943067042e+10
# HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
# TYPE go_memstats_gc_sys_bytes gauge
go_memstats_gc_sys_bytes 7.12454592e+08
# HELP go_memstats_heap_alloc_bytes Number of heap bytes allocated and still in use.
# TYPE go_memstats_heap_alloc_bytes gauge
go_memstats_heap_alloc_bytes 4.45263448e+09
# HELP go_memstats_heap_idle_bytes Number of heap bytes waiting to be used.
# TYPE go_memstats_heap_idle_bytes gauge
go_memstats_heap_idle_bytes 3.135340544e+10
# HELP go_memstats_heap_inuse_bytes Number of heap bytes that are in use.
# TYPE go_memstats_heap_inuse_bytes gauge
go_memstats_heap_inuse_bytes 4.68025344e+09
# HELP go_memstats_heap_objects Number of allocated objects.
# TYPE go_memstats_heap_objects gauge
go_memstats_heap_objects 2.866946e+07
# HELP go_memstats_heap_released_bytes Number of heap bytes released to OS.
# TYPE go_memstats_heap_released_bytes gauge
go_memstats_heap_released_bytes 3.0019944448e+10
# HELP go_memstats_heap_sys_bytes Number of heap bytes obtained from system.
# TYPE go_memstats_heap_sys_bytes gauge
go_memstats_heap_sys_bytes 3.603365888e+10
# HELP go_memstats_last_gc_time_seconds Number of seconds since 1970 of last garbage collection.
# TYPE go_memstats_last_gc_time_seconds gauge
go_memstats_last_gc_time_seconds 1.7097342808446639e+09
# HELP go_memstats_lookups_total Total number of pointer lookups.
# TYPE go_memstats_lookups_total counter
go_memstats_lookups_total 0
# HELP go_memstats_mallocs_total Total number of mallocs.
# TYPE go_memstats_mallocs_total counter
go_memstats_mallocs_total 1.8971736502e+10
# HELP go_memstats_mcache_inuse_bytes Number of bytes in use by mcache structures.
# TYPE go_memstats_mcache_inuse_bytes gauge
go_memstats_mcache_inuse_bytes 4800
# HELP go_memstats_mcache_sys_bytes Number of bytes used for mcache structures obtained from system.
# TYPE go_memstats_mcache_sys_bytes gauge
go_memstats_mcache_sys_bytes 15600
# HELP go_memstats_mspan_inuse_bytes Number of bytes in use by mspan structures.
# TYPE go_memstats_mspan_inuse_bytes gauge
go_memstats_mspan_inuse_bytes 3.689968e+07
# HELP go_memstats_mspan_sys_bytes Number of bytes used for mspan structures obtained from system.
# TYPE go_memstats_mspan_sys_bytes gauge
go_memstats_mspan_sys_bytes 1.0552512e+08
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
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="1"} 7067
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="2.5"} 7080
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="5"} 7080
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="10"} 7081
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="20"} 7081
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="40"} 7081
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="80"} 7081
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="160"} 7081
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="320"} 7081
grpc_server_handling_seconds_bucket{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary",le="+Inf"} 7081
grpc_server_handling_seconds_sum{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 90.8053342549999
grpc_server_handling_seconds_count{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 7081
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="0.5"} 123827
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="1"} 125343
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="2.5"} 126443
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="5"} 126797
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="10"} 126839
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="20"} 126842
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="40"} 126842
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="80"} 126842
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="160"} 126842
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="320"} 126842
grpc_server_handling_seconds_bucket{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="+Inf"} 126842
grpc_server_handling_seconds_sum{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 5701.520388515045
grpc_server_handling_seconds_count{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 126842
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="0.5"} 4242
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="1"} 4243
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="2.5"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="5"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="10"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="20"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="40"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="80"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="160"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="320"} 4244
grpc_server_handling_seconds_bucket{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary",le="+Inf"} 4244
grpc_server_handling_seconds_sum{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary"} 10.162107925999981
grpc_server_handling_seconds_count{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary"} 4244
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="0.5"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="1"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="2.5"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="5"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="10"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="20"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="40"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="80"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="160"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="320"} 1264
grpc_server_handling_seconds_bucket{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary",le="+Inf"} 1264
grpc_server_handling_seconds_sum{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary"} 0.47458033499999935
grpc_server_handling_seconds_count{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary"} 1264
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="0.5"} 1.5011939e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="1"} 1.5460193e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="2.5"} 1.58212e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="5"} 1.5901923e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="10"} 1.5902288e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="20"} 1.5902313e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="40"} 1.5902313e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="80"} 1.5902313e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="160"} 1.5902313e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="320"} 1.5902313e+07
grpc_server_handling_seconds_bucket{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream",le="+Inf"} 1.5902313e+07
grpc_server_handling_seconds_sum{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream"} 1.3858877291779632e+06
grpc_server_handling_seconds_count{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream"} 1.5902313e+07
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="0.5"} 7029
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="1"} 7045
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="2.5"} 7048
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="5"} 7049
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="10"} 7049
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="20"} 7049
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="40"} 7049
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="80"} 7049
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="160"} 7049
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="320"} 7049
grpc_server_handling_seconds_bucket{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary",le="+Inf"} 7049
grpc_server_handling_seconds_sum{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 55.3045959870001
grpc_server_handling_seconds_count{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 7049
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="0.5"} 221436
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="1"} 250340
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="2.5"} 288092
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="5"} 322437
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="10"} 356420
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="20"} 369391
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="40"} 369671
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="80"} 369674
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="160"} 369674
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="320"} 369674
grpc_server_handling_seconds_bucket{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream",le="+Inf"} 369674
grpc_server_handling_seconds_sum{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream"} 651964.5022437294
grpc_server_handling_seconds_count{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream"} 369674
# HELP grpc_server_msg_received_total Total number of RPC stream messages received on the server.
# TYPE grpc_server_msg_received_total counter
grpc_server_msg_received_total{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 7081
grpc_server_msg_received_total{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 126842
grpc_server_msg_received_total{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary"} 4244
grpc_server_msg_received_total{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary"} 1264
grpc_server_msg_received_total{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream"} 1.5902313e+07
grpc_server_msg_received_total{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 7049
grpc_server_msg_received_total{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream"} 692580
# HELP grpc_server_msg_sent_total Total number of gRPC stream messages sent by the server.
# TYPE grpc_server_msg_sent_total counter
grpc_server_msg_sent_total{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 7081
grpc_server_msg_sent_total{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 119882
grpc_server_msg_sent_total{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary"} 4244
grpc_server_msg_sent_total{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary"} 1264
grpc_server_msg_sent_total{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream"} 1.7463937e+07
grpc_server_msg_sent_total{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 7049
grpc_server_msg_sent_total{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream"} 369674
# HELP grpc_server_started_total Total number of RPCs started on the server.
# TYPE grpc_server_started_total counter
grpc_server_started_total{grpc_method="FindMissingBlobs",grpc_service="build.bazel.remote.execution.v2.ContentAddressableStorage",grpc_type="unary"} 7081
grpc_server_started_total{grpc_method="GetActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 126842
grpc_server_started_total{grpc_method="GetCapabilities",grpc_service="build.bazel.remote.execution.v2.Capabilities",grpc_type="unary"} 4244
grpc_server_started_total{grpc_method="QueryWriteStatus",grpc_service="google.bytestream.ByteStream",grpc_type="unary"} 1264
grpc_server_started_total{grpc_method="Read",grpc_service="google.bytestream.ByteStream",grpc_type="server_stream"} 1.5902313e+07
grpc_server_started_total{grpc_method="UpdateActionResult",grpc_service="build.bazel.remote.execution.v2.ActionCache",grpc_type="unary"} 7049
grpc_server_started_total{grpc_method="Write",grpc_service="google.bytestream.ByteStream",grpc_type="client_stream"} 369674
# HELP http_request_duration_seconds The latency of the HTTP requests.
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="0.5"} 961
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="1"} 968
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="2.5"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="5"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="10"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="20"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="40"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="80"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="160"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="320"} 972
http_request_duration_seconds_bucket{code="200",handler="metrics",method="GET",service="",le="+Inf"} 972
http_request_duration_seconds_sum{code="200",handler="metrics",method="GET",service=""} 20.28851677500002
http_request_duration_seconds_count{code="200",handler="metrics",method="GET",service=""} 972
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="0.5"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="1"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="2.5"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="5"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="10"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="20"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="40"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="80"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="160"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="320"} 2
http_request_duration_seconds_bucket{code="400",handler="GET",method="GET",service="",le="+Inf"} 2
http_request_duration_seconds_sum{code="400",handler="GET",method="GET",service=""} 0.001435642
http_request_duration_seconds_count{code="400",handler="GET",method="GET",service=""} 2
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="0.5"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="1"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="2.5"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="5"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="10"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="20"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="40"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="80"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="160"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="320"} 7659
http_request_duration_seconds_bucket{code="401",handler="GET",method="GET",service="",le="+Inf"} 7659
http_request_duration_seconds_sum{code="401",handler="GET",method="GET",service=""} 0.046080512000000136
http_request_duration_seconds_count{code="401",handler="GET",method="GET",service=""} 7659
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="0.5"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="1"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="2.5"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="5"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="10"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="20"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="40"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="80"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="160"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="320"} 4
http_request_duration_seconds_bucket{code="401",handler="HEAD",method="HEAD",service="",le="+Inf"} 4
http_request_duration_seconds_sum{code="401",handler="HEAD",method="HEAD",service=""} 3.0091e-05
http_request_duration_seconds_count{code="401",handler="HEAD",method="HEAD",service=""} 4
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="0.5"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="1"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="2.5"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="5"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="10"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="20"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="40"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="80"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="160"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="320"} 1
http_request_duration_seconds_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="+Inf"} 1
http_request_duration_seconds_sum{code="401",handler="KDFARY",method="KDFARY",service=""} 2.56e-06
http_request_duration_seconds_count{code="401",handler="KDFARY",method="KDFARY",service=""} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="0.5"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="1"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="2.5"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="5"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="10"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="20"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="40"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="80"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="160"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="320"} 1
http_request_duration_seconds_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="+Inf"} 1
http_request_duration_seconds_sum{code="401",handler="NESSUS",method="NESSUS",service=""} 2.96e-06
http_request_duration_seconds_count{code="401",handler="NESSUS",method="NESSUS",service=""} 1
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="0.5"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="1"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="2.5"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="5"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="10"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="20"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="40"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="80"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="160"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="320"} 2
http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="+Inf"} 2
http_request_duration_seconds_sum{code="401",handler="OPTIONS",method="OPTIONS",service=""} 7.44e-06
http_request_duration_seconds_count{code="401",handler="OPTIONS",method="OPTIONS",service=""} 2
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="0.5"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="1"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="2.5"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="5"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="10"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="20"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="40"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="80"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="160"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="320"} 101
http_request_duration_seconds_bucket{code="401",handler="POST",method="POST",service="",le="+Inf"} 101
http_request_duration_seconds_sum{code="401",handler="POST",method="POST",service=""} 0.000607423
http_request_duration_seconds_count{code="401",handler="POST",method="POST",service=""} 101
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="0.5"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="1"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="2.5"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="5"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="10"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="20"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="40"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="80"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="160"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="320"} 1
http_request_duration_seconds_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="+Inf"} 1
http_request_duration_seconds_sum{code="401",handler="PROPFIND",method="PROPFIND",service=""} 7.68e-06
http_request_duration_seconds_count{code="401",handler="PROPFIND",method="PROPFIND",service=""} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="0.5"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="1"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="2.5"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="5"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="10"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="20"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="40"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="80"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="160"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="320"} 1
http_request_duration_seconds_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="+Inf"} 1
http_request_duration_seconds_sum{code="401",handler="SEARCH",method="SEARCH",service=""} 3.37e-06
http_request_duration_seconds_count{code="401",handler="SEARCH",method="SEARCH",service=""} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="0.5"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="1"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="2.5"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="5"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="10"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="20"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="40"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="80"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="160"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="320"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACE",method="TRACE",service="",le="+Inf"} 1
http_request_duration_seconds_sum{code="401",handler="TRACE",method="TRACE",service=""} 7.771e-06
http_request_duration_seconds_count{code="401",handler="TRACE",method="TRACE",service=""} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="0.5"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="1"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="2.5"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="5"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="10"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="20"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="40"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="80"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="160"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="320"} 1
http_request_duration_seconds_bucket{code="401",handler="TRACK",method="TRACK",service="",le="+Inf"} 1
http_request_duration_seconds_sum{code="401",handler="TRACK",method="TRACK",service=""} 6.01e-06
http_request_duration_seconds_count{code="401",handler="TRACK",method="TRACK",service=""} 1
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
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="1000"} 0
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="10000"} 972
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="100000"} 972
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="1e+06"} 972
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="1e+07"} 972
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="1e+08"} 972
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="1e+09"} 972
http_response_size_bytes_bucket{code="200",handler="metrics",method="GET",service="",le="+Inf"} 972
http_response_size_bytes_sum{code="200",handler="metrics",method="GET",service=""} 4.4765e+06
http_response_size_bytes_count{code="200",handler="metrics",method="GET",service=""} 972
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="100"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="1000"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="10000"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="100000"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="1e+06"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="1e+07"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="1e+08"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="1e+09"} 2
http_response_size_bytes_bucket{code="400",handler="GET",method="GET",service="",le="+Inf"} 2
http_response_size_bytes_sum{code="400",handler="GET",method="GET",service=""} 126
http_response_size_bytes_count{code="400",handler="GET",method="GET",service=""} 2
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="100"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="1000"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="10000"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="100000"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="1e+06"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="1e+07"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="1e+08"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="1e+09"} 7659
http_response_size_bytes_bucket{code="401",handler="GET",method="GET",service="",le="+Inf"} 7659
http_response_size_bytes_sum{code="401",handler="GET",method="GET",service=""} 130203
http_response_size_bytes_count{code="401",handler="GET",method="GET",service=""} 7659
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="100"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="1000"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="10000"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="100000"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="1e+06"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="1e+07"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="1e+08"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="1e+09"} 4
http_response_size_bytes_bucket{code="401",handler="HEAD",method="HEAD",service="",le="+Inf"} 4
http_response_size_bytes_sum{code="401",handler="HEAD",method="HEAD",service=""} 68
http_response_size_bytes_count{code="401",handler="HEAD",method="HEAD",service=""} 4
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="100"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="1000"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="10000"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="100000"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="1e+06"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="1e+07"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="1e+08"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="1e+09"} 1
http_response_size_bytes_bucket{code="401",handler="KDFARY",method="KDFARY",service="",le="+Inf"} 1
http_response_size_bytes_sum{code="401",handler="KDFARY",method="KDFARY",service=""} 17
http_response_size_bytes_count{code="401",handler="KDFARY",method="KDFARY",service=""} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="100"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="1000"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="10000"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="100000"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="1e+06"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="1e+07"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="1e+08"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="1e+09"} 1
http_response_size_bytes_bucket{code="401",handler="NESSUS",method="NESSUS",service="",le="+Inf"} 1
http_response_size_bytes_sum{code="401",handler="NESSUS",method="NESSUS",service=""} 17
http_response_size_bytes_count{code="401",handler="NESSUS",method="NESSUS",service=""} 1
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="100"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="1000"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="10000"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="100000"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="1e+06"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="1e+07"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="1e+08"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="1e+09"} 2
http_response_size_bytes_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="+Inf"} 2
http_response_size_bytes_sum{code="401",handler="OPTIONS",method="OPTIONS",service=""} 34
http_response_size_bytes_count{code="401",handler="OPTIONS",method="OPTIONS",service=""} 2
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="100"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="1000"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="10000"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="100000"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="1e+06"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="1e+07"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="1e+08"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="1e+09"} 101
http_response_size_bytes_bucket{code="401",handler="POST",method="POST",service="",le="+Inf"} 101
http_response_size_bytes_sum{code="401",handler="POST",method="POST",service=""} 1717
http_response_size_bytes_count{code="401",handler="POST",method="POST",service=""} 101
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="100"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="1000"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="10000"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="100000"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="1e+06"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="1e+07"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="1e+08"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="1e+09"} 1
http_response_size_bytes_bucket{code="401",handler="PROPFIND",method="PROPFIND",service="",le="+Inf"} 1
http_response_size_bytes_sum{code="401",handler="PROPFIND",method="PROPFIND",service=""} 17
http_response_size_bytes_count{code="401",handler="PROPFIND",method="PROPFIND",service=""} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="100"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="1000"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="10000"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="100000"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="1e+06"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="1e+07"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="1e+08"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="1e+09"} 1
http_response_size_bytes_bucket{code="401",handler="SEARCH",method="SEARCH",service="",le="+Inf"} 1
http_response_size_bytes_sum{code="401",handler="SEARCH",method="SEARCH",service=""} 17
http_response_size_bytes_count{code="401",handler="SEARCH",method="SEARCH",service=""} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="100"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="1000"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="10000"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="100000"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="1e+06"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="1e+07"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="1e+08"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="1e+09"} 1
http_response_size_bytes_bucket{code="401",handler="TRACE",method="TRACE",service="",le="+Inf"} 1
http_response_size_bytes_sum{code="401",handler="TRACE",method="TRACE",service=""} 17
http_response_size_bytes_count{code="401",handler="TRACE",method="TRACE",service=""} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="100"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="1000"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="10000"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="100000"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="1e+06"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="1e+07"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="1e+08"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="1e+09"} 1
http_response_size_bytes_bucket{code="401",handler="TRACK",method="TRACK",service="",le="+Inf"} 1
http_response_size_bytes_sum{code="401",handler="TRACK",method="TRACK",service=""} 17
http_response_size_bytes_count{code="401",handler="TRACK",method="TRACK",service=""} 1
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
# HELP promhttp_metric_handler_requests_in_flight Current number of scrapes being served.
# TYPE promhttp_metric_handler_requests_in_flight gauge
promhttp_metric_handler_requests_in_flight 1
# HELP promhttp_metric_handler_requests_total Total number of scrapes by HTTP status code.
# TYPE promhttp_metric_handler_requests_total counter
promhttp_metric_handler_requests_total{code="200"} 972
promhttp_metric_handler_requests_total{code="500"} 0
promhttp_metric_handler_requests_total{code="503"} 0
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
def test_agent_bazel_cache_main(capsys: pytest.CaptureFixture[str]) -> None:
    arg_list = [
        "--host",
        "bazel-cache.tld",
    ]
    args = parse_arguments(arg_list)

    result_code = agent_bazel_cache_main(args=args)
    captured = capsys.readouterr()
    assert captured.out.rstrip().split("\n") == [
        "<<<bazel_cache_status:sep(0)>>>",
        '{"curr_size": 283741868032, '
        '"git_commit": "c5bf6e13938aa89923c637b5a4f01c2203a3c9f8", '
        '"max_size": 483183820800, '
        '"num_files": 15967454, '
        '"num_goroutines": 9, '
        '"reserved_size": 0, '
        '"server_time": 1714376779, '
        '"uncompressed_size": 668958797824}',
        # comment for easier reading
        "<<<bazel_cache_metrics:sep(0)>>>",
        '{"bazel_remote_azblob_cache_hits": "0", '
        '"bazel_remote_azblob_cache_misses": "0", '
        '"bazel_remote_disk_cache_evicted_bytes_total": "0", '
        '"bazel_remote_disk_cache_logical_bytes": "2.6872918016e+11", '
        '"bazel_remote_disk_cache_longest_item_idle_time_seconds": "1.257133290844899e+06", '
        '"bazel_remote_disk_cache_overwritten_bytes_total": "140096", '
        '"bazel_remote_disk_cache_size_bytes": "1.1447904256e+11", '
        '"bazel_remote_http_cache_hits": "0", '
        '"bazel_remote_http_cache_misses": "0", '
        '"bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit": "119882", '
        '"bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss": "6960", '
        '"bazel_remote_incoming_requests_total_kind_cas_method_contains_status_hit": "1.185848e+06", '
        '"bazel_remote_incoming_requests_total_kind_cas_method_contains_status_miss": "740637", '
        '"bazel_remote_incoming_requests_total_kind_cas_method_get_status_hit": "1.5902261e+07", '
        '"bazel_remote_incoming_requests_total_kind_cas_method_get_status_miss": "52", '
        '"bazel_remote_s3_cache_hits": "0", '
        '"bazel_remote_s3_cache_misses": "0", '
        '"process_cpu_seconds_total": "17190.38", '
        '"process_max_fds": "1.048576e+06", '
        '"process_open_fds": "32", '
        '"process_resident_memory_bytes": "6.821412864e+09", '
        '"process_start_time_seconds": "1.70967396224e+09", '
        '"process_virtual_memory_bytes": "4.2206461952e+10", '
        '"process_virtual_memory_max_bytes": "1.8446744073709552e+19", '
        '"promhttp_metric_handler_requests_in_flight": "1", '
        '"promhttp_metric_handler_requests_total_code_200": "972", '
        '"promhttp_metric_handler_requests_total_code_500": "0", '
        '"promhttp_metric_handler_requests_total_code_503": "0"}',
        # comment for easier reading
        "<<<bazel_cache_metrics_go:sep(0)>>>",
        '{"go_gc_duration_seconds_count": "968", '
        '"go_gc_duration_seconds_quantile_0": "9.4473e-05", '
        '"go_gc_duration_seconds_quantile_0_25": "0.000274378", '
        '"go_gc_duration_seconds_quantile_0_5": "0.000487193", '
        '"go_gc_duration_seconds_quantile_0_75": "0.000784432", '
        '"go_gc_duration_seconds_quantile_1": "0.005608786", '
        '"go_gc_duration_seconds_sum": "0.803301822", '
        '"go_goroutines": "76", '
        '"go_info": "1", '
        '"go_memstats_alloc_bytes": "4.45263448e+09", '
        '"go_memstats_alloc_bytes_total": "2.979080746328e+12", '
        '"go_memstats_buck_hash_sys_bytes": "2.336119e+06", '
        '"go_memstats_frees_total": "1.8943067042e+10", '
        '"go_memstats_gc_sys_bytes": "7.12454592e+08", '
        '"go_memstats_heap_alloc_bytes": "4.45263448e+09", '
        '"go_memstats_heap_idle_bytes": "3.135340544e+10", '
        '"go_memstats_heap_inuse_bytes": "4.68025344e+09", '
        '"go_memstats_heap_objects": "2.866946e+07", '
        '"go_memstats_heap_released_bytes": "3.0019944448e+10", '
        '"go_memstats_heap_sys_bytes": "3.603365888e+10", '
        '"go_memstats_last_gc_time_seconds": "1.7097342808446639e+09", '
        '"go_memstats_lookups_total": "0", '
        '"go_memstats_mallocs_total": "1.8971736502e+10", '
        '"go_memstats_mcache_inuse_bytes": "4800", '
        '"go_memstats_mcache_sys_bytes": "15600", '
        '"go_memstats_mspan_inuse_bytes": "3.689968e+07", '
        '"go_memstats_mspan_sys_bytes": "1.0552512e+08", '
        '"go_memstats_next_gc_bytes": "8.80778356e+09", '
        '"go_memstats_other_sys_bytes": "1.0149457e+07", '
        '"go_memstats_stack_inuse_bytes": "1.2189696e+07", '
        '"go_memstats_stack_sys_bytes": "1.2189696e+07", '
        '"go_memstats_sys_bytes": "3.6876329464e+10", '
        '"go_threads": "302"}',
        # comment for easier reading
        "<<<bazel_cache_metrics_grpc:sep(0)>>>",
        '{"grpc_server_handled_total_grpc_code_NotFound_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "6960", '
        '"grpc_server_handled_total_grpc_code_NotFound_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream": "52", '
        '"grpc_server_handled_total_grpc_code_OK_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary": "7081", '
        '"grpc_server_handled_total_grpc_code_OK_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "119882", '
        '"grpc_server_handled_total_grpc_code_OK_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary": "4244", '
        '"grpc_server_handled_total_grpc_code_OK_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary": "1264", '
        '"grpc_server_handled_total_grpc_code_OK_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream": "1.5902261e+07", '
        '"grpc_server_handled_total_grpc_code_OK_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "7049", '
        '"grpc_server_handled_total_grpc_code_OK_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream": "369674", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_+Inf": "7081", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_0_5": "7030", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_1": "7067", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_10": "7081", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_160": "7081", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_20": "7081", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_2_5": "7080", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_320": "7081", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_40": "7081", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_5": "7080", '
        '"grpc_server_handling_seconds_bucket_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary_le_80": "7081", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_+Inf": "126842", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_0_5": "123827", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_1": "125343", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_10": "126839", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_160": "126842", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_20": "126842", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_2_5": "126443", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_320": "126842", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_40": "126842", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_5": "126797", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_80": "126842", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_+Inf": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_0_5": "4242", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_1": "4243", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_10": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_160": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_20": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_2_5": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_320": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_40": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_5": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary_le_80": "4244", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_+Inf": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_0_5": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_1": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_10": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_160": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_20": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_2_5": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_320": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_40": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_5": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary_le_80": "1264", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_+Inf": "1.5902313e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_0_5": "1.5011939e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_1": "1.5460193e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_10": "1.5902288e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_160": "1.5902313e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_20": "1.5902313e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_2_5": "1.58212e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_320": "1.5902313e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_40": "1.5902313e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_5": "1.5901923e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream_le_80": "1.5902313e+07", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_+Inf": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_0_5": "7029", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_1": "7045", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_10": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_160": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_20": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_2_5": "7048", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_320": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_40": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_5": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary_le_80": "7049", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_+Inf": "369674", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_0_5": "221436", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_1": "250340", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_10": "356420", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_160": "369674", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_20": "369391", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_2_5": "288092", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_320": "369674", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_40": "369671", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_5": "322437", '
        '"grpc_server_handling_seconds_bucket_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream_le_80": "369674", '
        '"grpc_server_handling_seconds_count_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary": "7081", '
        '"grpc_server_handling_seconds_count_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "126842", '
        '"grpc_server_handling_seconds_count_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary": "4244", '
        '"grpc_server_handling_seconds_count_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary": "1264", '
        '"grpc_server_handling_seconds_count_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream": "1.5902313e+07", '
        '"grpc_server_handling_seconds_count_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "7049", '
        '"grpc_server_handling_seconds_count_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream": "369674", '
        '"grpc_server_handling_seconds_sum_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary": "90.8053342549999", '
        '"grpc_server_handling_seconds_sum_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "5701.520388515045", '
        '"grpc_server_handling_seconds_sum_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary": "10.162107925999981", '
        '"grpc_server_handling_seconds_sum_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary": "0.47458033499999935", '
        '"grpc_server_handling_seconds_sum_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream": "1.3858877291779632e+06", '
        '"grpc_server_handling_seconds_sum_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "55.3045959870001", '
        '"grpc_server_handling_seconds_sum_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream": "651964.5022437294", '
        '"grpc_server_msg_received_total_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary": "7081", '
        '"grpc_server_msg_received_total_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "126842", '
        '"grpc_server_msg_received_total_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary": "4244", '
        '"grpc_server_msg_received_total_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary": "1264", '
        '"grpc_server_msg_received_total_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream": "1.5902313e+07", '
        '"grpc_server_msg_received_total_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "7049", '
        '"grpc_server_msg_received_total_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream": "692580", '
        '"grpc_server_msg_sent_total_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary": "7081", '
        '"grpc_server_msg_sent_total_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "119882", '
        '"grpc_server_msg_sent_total_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary": "4244", '
        '"grpc_server_msg_sent_total_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary": "1264", '
        '"grpc_server_msg_sent_total_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream": "1.7463937e+07", '
        '"grpc_server_msg_sent_total_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "7049", '
        '"grpc_server_msg_sent_total_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream": "369674", '
        '"grpc_server_started_total_grpc_method_FindMissingBlobs_grpc_service_build_bazel_remote_execution_v2_ContentAddressableStorage_grpc_type_unary": "7081", '
        '"grpc_server_started_total_grpc_method_GetActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "126842", '
        '"grpc_server_started_total_grpc_method_GetCapabilities_grpc_service_build_bazel_remote_execution_v2_Capabilities_grpc_type_unary": "4244", '
        '"grpc_server_started_total_grpc_method_QueryWriteStatus_grpc_service_google_bytestream_ByteStream_grpc_type_unary": "1264", '
        '"grpc_server_started_total_grpc_method_Read_grpc_service_google_bytestream_ByteStream_grpc_type_server_stream": "1.5902313e+07", '
        '"grpc_server_started_total_grpc_method_UpdateActionResult_grpc_service_build_bazel_remote_execution_v2_ActionCache_grpc_type_unary": "7049", '
        '"grpc_server_started_total_grpc_method_Write_grpc_service_google_bytestream_ByteStream_grpc_type_client_stream": "369674"}',
        # comment for easier reading
        "<<<bazel_cache_metrics_http:sep(0)>>>",
        '{"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_+Inf": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_0_5": "961", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_1": "968", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_10": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_160": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_20": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_2_5": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_320": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_40": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_5": "972", '
        '"http_request_duration_seconds_bucket_code_200_handler_metrics_method_GET_le_80": "972", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_+Inf": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_0_5": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_1": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_10": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_160": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_20": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_2_5": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_320": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_40": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_5": "2", '
        '"http_request_duration_seconds_bucket_code_400_handler_GET_method_GET_le_80": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_+Inf": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_0_5": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_1": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_10": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_160": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_20": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_2_5": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_320": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_40": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_5": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_GET_method_GET_le_80": "7659", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_+Inf": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_0_5": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_1": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_10": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_160": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_20": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_2_5": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_320": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_40": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_5": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_HEAD_method_HEAD_le_80": "4", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_+Inf": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_0_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_1": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_10": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_160": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_20": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_2_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_320": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_40": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_KDFARY_method_KDFARY_le_80": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_+Inf": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_0_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_1": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_10": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_160": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_20": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_2_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_320": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_40": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_NESSUS_method_NESSUS_le_80": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_+Inf": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_0_5": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_1": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_10": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_160": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_20": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_2_5": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_320": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_40": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_5": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_80": "2", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_+Inf": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_0_5": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_1": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_10": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_160": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_20": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_2_5": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_320": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_40": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_5": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_POST_method_POST_le_80": "101", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_+Inf": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_0_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_1": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_10": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_160": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_20": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_2_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_320": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_40": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_80": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_+Inf": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_0_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_1": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_10": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_160": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_20": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_2_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_320": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_40": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_SEARCH_method_SEARCH_le_80": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_+Inf": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_0_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_1": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_10": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_160": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_20": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_2_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_320": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_40": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACE_method_TRACE_le_80": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_+Inf": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_0_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_1": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_10": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_160": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_20": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_2_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_320": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_40": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_5": "1", '
        '"http_request_duration_seconds_bucket_code_401_handler_TRACK_method_TRACK_le_80": "1", '
        '"http_request_duration_seconds_count_code_200_handler_metrics_method_GET": "972", '
        '"http_request_duration_seconds_count_code_400_handler_GET_method_GET": "2", '
        '"http_request_duration_seconds_count_code_401_handler_GET_method_GET": "7659", '
        '"http_request_duration_seconds_count_code_401_handler_HEAD_method_HEAD": "4", '
        '"http_request_duration_seconds_count_code_401_handler_KDFARY_method_KDFARY": "1", '
        '"http_request_duration_seconds_count_code_401_handler_NESSUS_method_NESSUS": "1", '
        '"http_request_duration_seconds_count_code_401_handler_OPTIONS_method_OPTIONS": "2", '
        '"http_request_duration_seconds_count_code_401_handler_POST_method_POST": "101", '
        '"http_request_duration_seconds_count_code_401_handler_PROPFIND_method_PROPFIND": "1", '
        '"http_request_duration_seconds_count_code_401_handler_SEARCH_method_SEARCH": "1", '
        '"http_request_duration_seconds_count_code_401_handler_TRACE_method_TRACE": "1", '
        '"http_request_duration_seconds_count_code_401_handler_TRACK_method_TRACK": "1", '
        '"http_request_duration_seconds_sum_code_200_handler_metrics_method_GET": "20.28851677500002", '
        '"http_request_duration_seconds_sum_code_400_handler_GET_method_GET": "0.001435642", '
        '"http_request_duration_seconds_sum_code_401_handler_GET_method_GET": "0.046080512000000136", '
        '"http_request_duration_seconds_sum_code_401_handler_HEAD_method_HEAD": "3.0091e-05", '
        '"http_request_duration_seconds_sum_code_401_handler_KDFARY_method_KDFARY": "2.56e-06", '
        '"http_request_duration_seconds_sum_code_401_handler_NESSUS_method_NESSUS": "2.96e-06", '
        '"http_request_duration_seconds_sum_code_401_handler_OPTIONS_method_OPTIONS": "7.44e-06", '
        '"http_request_duration_seconds_sum_code_401_handler_POST_method_POST": "0.000607423", '
        '"http_request_duration_seconds_sum_code_401_handler_PROPFIND_method_PROPFIND": "7.68e-06", '
        '"http_request_duration_seconds_sum_code_401_handler_SEARCH_method_SEARCH": "3.37e-06", '
        '"http_request_duration_seconds_sum_code_401_handler_TRACE_method_TRACE": "7.771e-06", '
        '"http_request_duration_seconds_sum_code_401_handler_TRACK_method_TRACK": "6.01e-06", '
        '"http_requests_inflight_handler_GET": "0", '
        '"http_requests_inflight_handler_HEAD": "0", '
        '"http_requests_inflight_handler_KDFARY": "0", '
        '"http_requests_inflight_handler_NESSUS": "0", '
        '"http_requests_inflight_handler_OPTIONS": "0", '
        '"http_requests_inflight_handler_POST": "0", '
        '"http_requests_inflight_handler_PROPFIND": "0", '
        '"http_requests_inflight_handler_SEARCH": "0", '
        '"http_requests_inflight_handler_TRACE": "0", '
        '"http_requests_inflight_handler_TRACK": "0", '
        '"http_requests_inflight_handler_metrics": "1", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_+Inf": "972", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_100": "0", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_1000": "0", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_10000": "972", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_100000": "972", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_1e+06": "972", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_1e+07": "972", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_1e+08": "972", '
        '"http_response_size_bytes_bucket_code_200_handler_metrics_method_GET_le_1e+09": "972", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_+Inf": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_100": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_1000": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_10000": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_100000": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_1e+06": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_1e+07": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_1e+08": "2", '
        '"http_response_size_bytes_bucket_code_400_handler_GET_method_GET_le_1e+09": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_+Inf": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_100": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_1000": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_10000": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_100000": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_1e+06": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_1e+07": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_1e+08": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_GET_method_GET_le_1e+09": "7659", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_+Inf": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_100": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_1000": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_10000": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_100000": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_1e+06": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_1e+07": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_1e+08": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_HEAD_method_HEAD_le_1e+09": "4", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_+Inf": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_100": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_1000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_10000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_100000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_1e+06": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_1e+07": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_1e+08": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_KDFARY_method_KDFARY_le_1e+09": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_+Inf": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_100": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_1000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_10000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_100000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_1e+06": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_1e+07": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_1e+08": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_NESSUS_method_NESSUS_le_1e+09": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_+Inf": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_100": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_1000": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_10000": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_100000": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_1e+06": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_1e+07": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_1e+08": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_1e+09": "2", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_+Inf": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_100": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_1000": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_10000": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_100000": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_1e+06": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_1e+07": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_1e+08": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_POST_method_POST_le_1e+09": "101", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_+Inf": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_100": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_1000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_10000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_100000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_1e+06": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_1e+07": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_1e+08": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_PROPFIND_method_PROPFIND_le_1e+09": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_+Inf": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_100": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_1000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_10000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_100000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_1e+06": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_1e+07": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_1e+08": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_SEARCH_method_SEARCH_le_1e+09": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_+Inf": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_100": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_1000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_10000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_100000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_1e+06": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_1e+07": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_1e+08": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACE_method_TRACE_le_1e+09": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_+Inf": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_100": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_1000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_10000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_100000": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_1e+06": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_1e+07": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_1e+08": "1", '
        '"http_response_size_bytes_bucket_code_401_handler_TRACK_method_TRACK_le_1e+09": "1", '
        '"http_response_size_bytes_count_code_200_handler_metrics_method_GET": "972", '
        '"http_response_size_bytes_count_code_400_handler_GET_method_GET": "2", '
        '"http_response_size_bytes_count_code_401_handler_GET_method_GET": "7659", '
        '"http_response_size_bytes_count_code_401_handler_HEAD_method_HEAD": "4", '
        '"http_response_size_bytes_count_code_401_handler_KDFARY_method_KDFARY": "1", '
        '"http_response_size_bytes_count_code_401_handler_NESSUS_method_NESSUS": "1", '
        '"http_response_size_bytes_count_code_401_handler_OPTIONS_method_OPTIONS": "2", '
        '"http_response_size_bytes_count_code_401_handler_POST_method_POST": "101", '
        '"http_response_size_bytes_count_code_401_handler_PROPFIND_method_PROPFIND": "1", '
        '"http_response_size_bytes_count_code_401_handler_SEARCH_method_SEARCH": "1", '
        '"http_response_size_bytes_count_code_401_handler_TRACE_method_TRACE": "1", '
        '"http_response_size_bytes_count_code_401_handler_TRACK_method_TRACK": "1", '
        '"http_response_size_bytes_sum_code_200_handler_metrics_method_GET": "4.4765e+06", '
        '"http_response_size_bytes_sum_code_400_handler_GET_method_GET": "126", '
        '"http_response_size_bytes_sum_code_401_handler_GET_method_GET": "130203", '
        '"http_response_size_bytes_sum_code_401_handler_HEAD_method_HEAD": "68", '
        '"http_response_size_bytes_sum_code_401_handler_KDFARY_method_KDFARY": "17", '
        '"http_response_size_bytes_sum_code_401_handler_NESSUS_method_NESSUS": "17", '
        '"http_response_size_bytes_sum_code_401_handler_OPTIONS_method_OPTIONS": "34", '
        '"http_response_size_bytes_sum_code_401_handler_POST_method_POST": "1717", '
        '"http_response_size_bytes_sum_code_401_handler_PROPFIND_method_PROPFIND": "17", '
        '"http_response_size_bytes_sum_code_401_handler_SEARCH_method_SEARCH": "17", '
        '"http_response_size_bytes_sum_code_401_handler_TRACE_method_TRACE": "17", '
        '"http_response_size_bytes_sum_code_401_handler_TRACK_method_TRACK": "17"}',
    ]
    assert captured.err == ""
    assert result_code == 0
