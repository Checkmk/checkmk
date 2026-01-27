#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from pathlib import Path

import pytest
import vcr  # type: ignore[import-untyped,unused-ignore]

from cmk.plugins.graylog.special_agent.agent_graylog import main

DIR_PATH = Path(os.path.dirname(__file__))
GRAYLOG_DEFAULT_ARGS = [
    "--user",
    "admin",
    "--password",
    "password",
    "-p9000",
    "--proto",
    "http",
    "127.0.0.1",
]
GRAYLOG_EXAMPLE_OUTPUT = """<<<graylog_cluster_stats:sep(0)>>>
{"stream_count": 3, "stream_rule_count": 0, "stream_rule_count_by_stream": {"000000000000000000000001": 0, "000000000000000000000002": 0, "000000000000000000000003": 0}, "user_count": 1, "output_count": 0, "output_count_by_type": {}, "dashboard_count": 1, "input_count": 1, "global_input_count": 0, "input_count_by_type": {"org.graylog2.inputs.raw.tcp.RawTCPInput": 1, "org.graylog2.inputs.raw.udp.RawUDPInput": 1}, "extractor_count": 0, "extractor_count_by_type": {}, "elasticsearch": {"cluster_name": "docker-cluster", "cluster_version": "2.4.0", "status": "Green", "cluster_health": {"number_of_nodes": 1, "number_of_data_nodes": 1, "active_shards": 12, "relocating_shards": 0, "active_primary_shards": 12, "initializing_shards": 0, "unassigned_shards": 0, "timed_out": false, "pending_tasks": 0, "pending_tasks_time_in_queue": []}, "nodes_stats": {"total": 1, "master_only": -1, "data_only": -1, "master_data": -1, "client": -1}, "indices_stats": {"index_count": 3, "store_size": 70594, "field_data_size": 3644, "id_cache_size": 0}}, "mongo": {"servers": ["mongodb:27017"], "build_info": {"version": "5.0.31", "git_version": "973237567d45610d6976d5d489dfaaef6a52c2f9", "sys_info": "deprecated", "loader_flags": null, "compiler_flags": null, "allocator": "tcmalloc", "version_array": [5, 0, 31, 0], "javascript_engine": "mozjs", "bits": 64, "debug": false, "max_bson_object_size": 16777216}, "host_info": {"system": {"current_time": "2025-05-26T09:23:40.506Z", "hostname": "e89f83ee7383", "cpu_addr_size": 64, "mem_size_mb": 31463, "num_cores": 12, "cpu_arch": "x86_64", "numa_enabled": false}, "os": {"type": "Linux", "name": "Ubuntu", "version": "20.04"}, "extra": {"version_string": "Linux version 6.11.0-26-generic (buildd@lcy02-amd64-074) (x86_64-linux-gnu-gcc-13 (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0, GNU ld (GNU Binutils for Ubuntu) 2.42) #26~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Thu Apr 17 19:20:47 UTC 2", "libc_version": "2.31", "kernel_version": "6.11.0-26-generic", "cpu_frequency_mhz": "1155.080", "cpu_features": "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf tsc_known_freq pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb ssbd ibrs ibpb stibp ibrs_enhanced tpr_shadow flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid rdseed adx smap clflushopt clwb intel_pt sha_ni xsaveopt xsavec xgetbv1 xsaves split_lock_detect user_shstk avx_vnni dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp hwp_pkg_req hfi vnmi umip pku ospke waitpkg gfni vaes vpclmulqdq rdpid movdiri movdir64b fsrm md_clear serialize pconfig arch_lbr ibt flush_l1d arch_capabilities", "scheduler": null, "page_size": 4096, "num_pages": 8054739, "max_open_files": 1048576}}, "server_status": {"host": "e89f83ee7383", "version": "5.0.31", "process": "mongod", "pid": 1, "uptime": 11936, "uptime_millis": 11935695, "uptime_estimate": 11935, "local_time": "2025-05-26T12:42:24.009Z", "connections": {"current": 8, "available": 838852, "total_created": 11}, "network": {"bytes_in": 49902890, "bytes_out": 104932370, "num_requests": 157196}, "memory": {"bits": 64, "resident": 127, "virtual": 1509, "supported": true, "mapped": -1, "mapped_with_journal": -1}, "storage_engine": {"name": "wiredTiger"}}, "database_stats": {"db": "graylog", "collections": 38, "objects": 285, "avg_obj_size": 497.8456140350877, "data_size": 141886, "storage_size": 688128, "num_extents": null, "indexes": 94, "index_size": 1359872, "file_size": null, "ns_size_mb": null, "extent_free_list": null, "data_file_version": null}}}
<<<graylog_cluster_traffic:sep(0)>>>
{"from": "2025-05-25T00:00:00.000Z", "to": "2025-05-26T12:42:24.025Z", "input": {"2025-05-26T09:00:00.000Z": 0, "2025-05-26T10:00:00.000Z": 0, "2025-05-26T11:00:00.000Z": 0, "2025-05-26T12:00:00.000Z": 0}, "output": {"2025-05-26T09:00:00.000Z": 0, "2025-05-26T10:00:00.000Z": 0, "2025-05-26T11:00:00.000Z": 0, "2025-05-26T12:00:00.000Z": 0}, "decoded": {"2025-05-26T09:00:00.000Z": 0, "2025-05-26T10:00:00.000Z": 0, "2025-05-26T11:00:00.000Z": 0, "2025-05-26T12:00:00.000Z": 0}}
<<<graylog_failures:sep(0)>>>
{"count": 0, "ds_param_since": 1800, "failures": [], "total": 0}
<<<graylog_jvm:sep(0)>>>
{"jvm.memory.heap.used": 170099488, "jvm.memory.heap.committed": 239075328, "jvm.memory.heap.init": 515899392, "jvm.memory.heap.max": 8250195968, "jvm.memory.heap.usage": 0.020617630012640203}
<<<graylog_messages:sep(0)>>>
{"events": 15}
<<<graylog_nodes:sep(0)>>>
{"3b4fa139-8491-44af-90da-cf32061b50b9": {"facility": "graylog-server", "codename": "Noir", "node_id": "3b4fa139-8491-44af-90da-cf32061b50b9", "cluster_id": "da859203-6f3c-4fb6-9499-85e7229b26fc", "version": "5.0.13+083613e", "started_at": "2025-05-26T09:23:36.957Z", "hostname": "server", "lifecycle": "running", "lb_status": "alive", "timezone": "Etc/UTC", "operating_system": "Linux 6.11.0-26-generic", "is_processing": true, "journal": {"enabled": true, "append_events_per_second": 0, "read_events_per_second": 0, "uncommitted_journal_entries": 0, "journal_size": 0, "journal_size_limit": 5368709120, "number_of_segments": 1, "oldest_segment": "2025-05-26T09:23:37.027Z", "journal_config": {"directory": "file:///usr/share/graylog/data/journal/", "segment_size": 104857600, "segment_age": 3600000, "max_size": 5368709120, "max_age": 43200000, "flush_interval": 1000000, "flush_age": 60000}}, "inputstates": [{"id": "6827432a44a4084bad03a9d8", "state": "RUNNING", "started_at": "2025-05-26T09:23:38.678Z", "detailed_message": null, "message_input": {"title": "test", "global": false, "name": "Raw/Plaintext UDP", "content_pack": null, "created_at": "2025-05-16T13:52:42.276Z", "type": "org.graylog2.inputs.raw.udp.RawUDPInput", "creator_user_id": "admin", "attributes": {"recv_buffer_size": 262144, "port": 5555, "number_worker_threads": 12, "override_source": "foobar", "charset_name": "UTF-8", "bind_address": "0.0.0.0"}, "static_fields": {}, "node": "3b4fa139-8491-44af-90da-cf32061b50b9", "id": "6827432a44a4084bad03a9d8"}}, {"id": "68273b3848e232496b4733a9", "state": "RUNNING", "started_at": "2025-05-26T09:23:38.675Z", "detailed_message": null, "message_input": {"title": "test", "global": false, "name": "Raw/Plaintext TCP", "content_pack": null, "created_at": "2025-05-16T13:18:48.252Z", "type": "org.graylog2.inputs.raw.tcp.RawTCPInput", "creator_user_id": "admin", "attributes": {"recv_buffer_size": 1048576, "tcp_keepalive": false, "use_null_delimiter": false, "number_worker_threads": 12, "tls_client_auth_cert_file": "", "bind_address": "0.0.0.0", "tls_cert_file": "", "port": 5555, "tls_key_file": "", "tls_enable": false, "tls_key_password": "", "max_message_size": 2097152, "tls_client_auth": "disabled", "override_source": null, "charset_name": "UTF-8"}, "static_fields": {}, "node": "3b4fa139-8491-44af-90da-cf32061b50b9", "id": "68273b3848e232496b4733a9"}}]}}
<<<graylog_streams:sep(0)>>>
{"total": 3, "streams": [{"id": "000000000000000000000003", "creator_user_id": "admin", "outputs": [], "matching_type": "AND", "description": "Stream containing all system events created by Graylog", "created_at": "2025-05-16T08:59:53.236Z", "disabled": false, "rules": [], "title": "All system events", "content_pack": null, "remove_matches_from_default_stream": true, "index_set_id": "6826fe89552b937fa1988554", "is_editable": false, "is_default": false}, {"id": "000000000000000000000002", "creator_user_id": "admin", "outputs": [], "matching_type": "AND", "description": "Stream containing all events created by Graylog", "created_at": "2025-05-16T08:59:53.203Z", "disabled": false, "rules": [], "title": "All events", "content_pack": null, "remove_matches_from_default_stream": true, "index_set_id": "6826fe89552b937fa1988551", "is_editable": false, "is_default": false}, {"id": "000000000000000000000001", "creator_user_id": "local:admin", "outputs": [], "matching_type": "AND", "description": "Contains messages that are not explicitly routed to other streams", "created_at": "2025-05-16T08:59:51.350Z", "disabled": false, "rules": [], "title": "Default Stream", "content_pack": null, "remove_matches_from_default_stream": false, "index_set_id": "6826fe87552b937fa1988496", "is_editable": true, "is_default": true}]}
<<<graylog_events:sep(0)>>>
{"events": {"num_of_events": 0, "has_since_argument": false, "events_since": null, "num_of_events_in_range": 0}}
"""
GRAYLOG_EXAMPLE_SECTION_NON_DEFAULT_SECTIONS = """<<<graylog_cluster_health:sep(0)>>>
{"status": "green", "shards": {"active": 12, "initializing": 0, "relocating": 0, "unassigned": 0}}
<<<graylog_cluster_inputstates:sep(0)>>>
{"3b4fa139-8491-44af-90da-cf32061b50b9": [{"id": "6827432a44a4084bad03a9d8", "state": "RUNNING", "started_at": "2025-05-26T09:23:38.678Z", "detailed_message": null, "message_input": {"title": "test", "global": false, "name": "Raw/Plaintext UDP", "content_pack": null, "created_at": "2025-05-16T13:52:42.276Z", "type": "org.graylog2.inputs.raw.udp.RawUDPInput", "creator_user_id": "admin", "attributes": {"recv_buffer_size": 262144, "port": 5555, "number_worker_threads": 12, "override_source": "foobar", "charset_name": "UTF-8", "bind_address": "0.0.0.0"}, "static_fields": {}, "node": "3b4fa139-8491-44af-90da-cf32061b50b9", "id": "6827432a44a4084bad03a9d8"}}, {"id": "68273b3848e232496b4733a9", "state": "RUNNING", "started_at": "2025-05-26T09:23:38.675Z", "detailed_message": null, "message_input": {"title": "test", "global": false, "name": "Raw/Plaintext TCP", "content_pack": null, "created_at": "2025-05-16T13:18:48.252Z", "type": "org.graylog2.inputs.raw.tcp.RawTCPInput", "creator_user_id": "admin", "attributes": {"recv_buffer_size": 1048576, "tcp_keepalive": false, "use_null_delimiter": false, "number_worker_threads": 12, "tls_client_auth_cert_file": "", "bind_address": "0.0.0.0", "tls_cert_file": "", "port": 5555, "tls_key_file": "", "tls_enable": false, "tls_key_password": "", "max_message_size": 2097152, "tls_client_auth": "disabled", "override_source": null, "charset_name": "UTF-8"}, "static_fields": {}, "node": "3b4fa139-8491-44af-90da-cf32061b50b9", "id": "68273b3848e232496b4733a9"}}]}
"""
GRAYLOG_EXAMPLE_SOURCES_OUTPUT = """<<<graylog_sources:sep(0)>>>
{"sources": {"127.0.0.1": {"messages": 42, "has_since_argument": false, "source_since": null}, "172.16.0.1": {"messages": 32, "has_since_argument": false, "source_since": null}, "foo.bar.com": {"messages": 12, "has_since_argument": false, "source_since": null}}}
"""
GRAYLOG_EXAMPLE_SOURCES_OUTPUT_SINCE = """<<<graylog_sources:sep(0)>>>
{"sources": {"127.0.0.1": {"messages": 42, "has_since_argument": true, "source_since": 300, "messages_since": 22}, "172.16.0.1": {"messages": 32, "has_since_argument": true, "source_since": 300, "messages_since": 32}, "foo.bar.com": {"messages": 12, "has_since_argument": true, "source_since": 300}}}
"""
GRAYLOG_EXAMPLE_SOURCES_OUTPUT_SINCE_PIGGYBACK = """<<<<127.0.0.1>>>>
<<<graylog_sources:sep(0)>>>
{"sources": {"127.0.0.1": {"messages": 42, "has_since_argument": true, "source_since": 300, "messages_since": 22}}}
<<<<>>>>
<<<<172.16.0.1>>>>
<<<graylog_sources:sep(0)>>>
{"sources": {"172.16.0.1": {"messages": 32, "has_since_argument": true, "source_since": 300, "messages_since": 32}}}
<<<<>>>>
<<<<foo.bar.com>>>>
<<<graylog_sources:sep(0)>>>
{"sources": {"foo.bar.com": {"messages": 12, "has_since_argument": true, "source_since": 300}}}
<<<<>>>>
"""
GRAYLOG_EXAMPLE_STDERR = """Error: 404 Client Error: Not Found for url: http://127.0.0.1:9000/api/streams/alerts?limit=300
Error: 404 Client Error: Not Found for url: http://127.0.0.1:9000/api/plugins/org.graylog.plugins.license/licenses/status
Error: Could not parse sources response from API: 'Expecting value: line 1 column 1 (char 0)'
"""


def test_agent_graylog_main(capsys: pytest.CaptureFixture[str]) -> None:
    with vcr.use_cassette(  # type: ignore[no-untyped-call,unused-ignore]
        DIR_PATH / "graylog_vcrtrace.yaml", record_mode="once", filter_query_parameters=["since"]
    ):
        assert main(GRAYLOG_DEFAULT_ARGS) == 0
        out, err = capsys.readouterr()
    assert out == GRAYLOG_EXAMPLE_OUTPUT
    assert err == GRAYLOG_EXAMPLE_STDERR


def test_agent_graylog_non_default_params(capsys: pytest.CaptureFixture[str]) -> None:
    filepath = "%s/graylog_vcrtrace_non_default.yaml" % os.path.dirname(__file__)
    with vcr.use_cassette(  # type: ignore[no-untyped-call,unused-ignore]
        filepath, record_mode="once", filter_query_parameters=["since"]
    ):
        assert (
            main(GRAYLOG_DEFAULT_ARGS + ["--sections", "cluster_health,cluster_inputstates"]) == 0
        )
        out, err = capsys.readouterr()
        assert out == GRAYLOG_EXAMPLE_SECTION_NON_DEFAULT_SECTIONS
        assert err == ""


@pytest.mark.parametrize(
    "args, expected_output",
    [
        pytest.param(
            GRAYLOG_DEFAULT_ARGS + ["--sections", "sources"],
            GRAYLOG_EXAMPLE_SOURCES_OUTPUT,
            id="default",
        ),
        pytest.param(
            GRAYLOG_DEFAULT_ARGS + ["--sections", "sources", "--source_since", "300"],
            GRAYLOG_EXAMPLE_SOURCES_OUTPUT_SINCE,
            id="With since argument",
        ),
        pytest.param(
            GRAYLOG_DEFAULT_ARGS
            + [
                "--sections",
                "sources",
                "--source_since",
                "300",
                "--display_source_details",
                "source",
            ],
            GRAYLOG_EXAMPLE_SOURCES_OUTPUT_SINCE_PIGGYBACK,
            id="Piggyback with since argument",
        ),
    ],
)
def test_agent_graylog_section_sources(
    args: list[str], expected_output: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with vcr.use_cassette(  # type: ignore[no-untyped-call,unused-ignore]
        DIR_PATH / "graylog_vcrtrace_sources.yaml",
        record_mode="new_episodes",
    ):
        assert main(args) == 0
        out, err = capsys.readouterr()
    assert out == expected_output
    assert err == ""


def test_agent_graylog_main_500(capsys: pytest.CaptureFixture[str]) -> None:
    with vcr.use_cassette(  # type: ignore[no-untyped-call,unused-ignore]
        DIR_PATH / "graylog_vcrtrace_500.yaml",
        record_mode="once",
    ):
        assert main(GRAYLOG_DEFAULT_ARGS) == 2
        out, err = capsys.readouterr()
    assert out == ""
    assert (
        err
        == "Error: Request to Graylog API failed: '500 Server Error: Internal Server Error for url: http://127.0.0.1:9000/api/system'\n"
    )
