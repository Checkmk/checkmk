#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from pathlib import Path

import pytest
import vcr  # type: ignore[import-untyped]

from cmk.plugins.graylog.special_agent.agent_graylog import main

GRAYLOG_DEFAULT_ARGS = [
    "-uadmin",
    "-spassword",
    "-p9000",
    "--proto",
    "http",
    "127.0.0.1",
]

GRAYLOG_EXAMPLE_OUTPUT = """<<<graylog_alerts:sep(0)>>>
{"alerts": {"num_of_alerts": 0, "has_since_argument": false, "alerts_since": null, "num_of_alerts_in_range": 0}}
<<<graylog_cluster_stats:sep(0)>>>
{"stream_count": 3, "stream_rule_count": 0, "stream_rule_count_by_stream": {"000000000000000000000001": 0, "000000000000000000000002": 0, "000000000000000000000003": 0}, "user_count": 1, "output_count": 0, "output_count_by_type": {}, "dashboard_count": 1, "input_count": 1, "global_input_count": 0, "input_count_by_type": {"org.graylog2.inputs.raw.tcp.RawTCPInput": 1, "org.graylog2.inputs.raw.udp.RawUDPInput": 1}, "extractor_count": 0, "extractor_count_by_type": {}, "elasticsearch": {"cluster_name": "docker-cluster", "cluster_version": "2.4.0", "status": "Green", "cluster_health": {"number_of_nodes": 1, "number_of_data_nodes": 1, "active_shards": 12, "relocating_shards": 0, "active_primary_shards": 12, "initializing_shards": 0, "unassigned_shards": 0, "timed_out": false, "pending_tasks": 0, "pending_tasks_time_in_queue": []}, "nodes_stats": {"total": 1, "master_only": -1, "data_only": -1, "master_data": -1, "client": -1}, "indices_stats": {"index_count": 3, "store_size": 70594, "field_data_size": 3644, "id_cache_size": 0}}, "mongo": {"servers": ["mongodb:27017"], "build_info": {"version": "5.0.31", "git_version": "973237567d45610d6976d5d489dfaaef6a52c2f9", "sys_info": "deprecated", "loader_flags": null, "compiler_flags": null, "allocator": "tcmalloc", "version_array": [5, 0, 31, 0], "javascript_engine": "mozjs", "bits": 64, "debug": false, "max_bson_object_size": 16777216}, "host_info": {"system": {"current_time": "2025-05-16T13:20:14.099Z", "hostname": "e89f83ee7383", "cpu_addr_size": 64, "mem_size_mb": 31463, "num_cores": 12, "cpu_arch": "x86_64", "numa_enabled": false}, "os": {"type": "Linux", "name": "Ubuntu", "version": "20.04"}, "extra": {"version_string": "Linux version 6.11.0-26-generic (buildd@lcy02-amd64-074) (x86_64-linux-gnu-gcc-13 (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0, GNU ld (GNU Binutils for Ubuntu) 2.42) #26~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Thu Apr 17 19:20:47 UTC 2", "libc_version": "2.31", "kernel_version": "6.11.0-26-generic", "cpu_frequency_mhz": "1199.850", "cpu_features": "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf tsc_known_freq pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb ssbd ibrs ibpb stibp ibrs_enhanced tpr_shadow flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid rdseed adx smap clflushopt clwb intel_pt sha_ni xsaveopt xsavec xgetbv1 xsaves split_lock_detect user_shstk avx_vnni dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp hwp_pkg_req hfi vnmi umip pku ospke waitpkg gfni vaes vpclmulqdq rdpid movdiri movdir64b fsrm md_clear serialize pconfig arch_lbr ibt flush_l1d arch_capabilities", "scheduler": null, "page_size": 4096, "num_pages": 8054738, "max_open_files": 1048576}}, "server_status": {"host": "e89f83ee7383", "version": "5.0.31", "process": "mongod", "pid": 1, "uptime": 240331, "uptime_millis": 240330659, "uptime_estimate": 240330, "local_time": "2025-05-19T08:04:42.521Z", "connections": {"current": 10, "available": 838850, "total_created": 13}, "network": {"bytes_in": 62166906, "bytes_out": 142331781, "num_requests": 226826}, "memory": {"bits": 64, "resident": 126, "virtual": 1519, "supported": true, "mapped": -1, "mapped_with_journal": -1}, "storage_engine": {"name": "wiredTiger"}}, "database_stats": {"db": "graylog", "collections": 38, "objects": 356, "avg_obj_size": 498.7752808988764, "data_size": 177564, "storage_size": 704512, "num_extents": null, "indexes": 94, "index_size": 1384448, "file_size": null, "ns_size_mb": null, "extent_free_list": null, "data_file_version": null}}}
<<<graylog_cluster_traffic:sep(0)>>>
{"from": "2025-05-18T00:00:00.000Z", "to": "2025-05-19T08:04:42.578Z", "input": {"2025-05-19T07:00:00.000Z": 0, "2025-05-19T08:00:00.000Z": 0}, "output": {"2025-05-19T07:00:00.000Z": 0, "2025-05-19T08:00:00.000Z": 0}, "decoded": {"2025-05-19T07:00:00.000Z": 0, "2025-05-19T08:00:00.000Z": 0}}
<<<graylog_failures:sep(0)>>>
{"count": 0, "failures": [], "total": 0, "ds_param_since": 1800}
<<<graylog_jvm:sep(0)>>>
{"jvm.memory.heap.used": 192217208, "jvm.memory.heap.committed": 281018368, "jvm.memory.heap.init": 515899392, "jvm.memory.heap.max": 8250195968, "jvm.memory.heap.usage": 0.02329850208959303}
<<<graylog_license:sep(0)>>>
{"type": "ApiError", "message": "HTTP 404 Not Found"}
"""

GRAYLOG_EXAMPLE_STDERR = """"""
DIR_PATH = Path(os.path.dirname(__file__))


def test_agent_graylog_main(capsys: pytest.CaptureFixture[str]) -> None:
    with vcr.use_cassette(
        DIR_PATH / "graylog_vcrtrace.json", record_mode="once", filter_query_parameters=["since"]
    ):
        assert main(GRAYLOG_DEFAULT_ARGS) == 0
        out, err = capsys.readouterr()
    assert out == GRAYLOG_EXAMPLE_OUTPUT
    assert err == GRAYLOG_EXAMPLE_STDERR


def test_agent_graylog_main_500(capsys: pytest.CaptureFixture[str]) -> None:
    with vcr.use_cassette(DIR_PATH / "graylog_vcrtrace_500.json", record_mode="once"):
        assert main(GRAYLOG_DEFAULT_ARGS) == 2
        out, err = capsys.readouterr()
    assert out == ""
    assert (
        err
        == "Error: Request to Graylog API failed: '500 Server Error: Internal Server Error for url: http://127.0.0.1:9000/api/system'\n"
    )
