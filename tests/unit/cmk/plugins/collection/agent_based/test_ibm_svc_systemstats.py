#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.ibm_svc_systemstats import (
    check_ibm_svc_systemstats_cache,
    check_ibm_svc_systemstats_cpu,
    check_ibm_svc_systemstats_disk_latency,
    check_ibm_svc_systemstats_diskio,
    check_ibm_svc_systemstats_iops,
    discovery_ibm_svc_systemstats_cache,
    discovery_ibm_svc_systemstats_cpu,
    discovery_ibm_svc_systemstats_disks,
    ibm_svc_systemstats_parse,
    IBMSystemStats,
)

TEST_INFO: Sequence[Sequence[str]] = [
    ["stat_name", "stat_current", "stat_peak", "stat_peak_time"],
    ["compression_cpu_pc", "0", "0", "220623092541"],
    ["cpu_pc", "91", "95", "220623092516"],
    ["fc_mb", "0", "0", "220623092541"],
    ["fc_io", "20", "21", "220623092536"],
    ["sas_mb", "39", "372", "220623092516"],
    ["sas_io", "154", "1482", "220623092516"],
    ["iscsi_mb", "0", "0", "220623092541"],
    ["iscsi_io", "0", "0", "220623092541"],
    ["write_cache_pc", "0", "0", "220623092541"],
    ["total_cache_pc", "2", "2", "220623092541"],
    ["vdisk_mb", "0", "0", "220623092541"],
    ["vdisk_io", "0", "0", "220623092541"],
    ["vdisk_ms", "0", "0", "220623092541"],
    ["mdisk_mb", "0", "0", "220623092541"],
    ["mdisk_io", "0", "0", "220623092541"],
    ["mdisk_ms", "0", "0", "220623092541"],
    ["drive_mb", "39", "372", "220623092516"],
    ["drive_io", "155", "1484", "220623092516"],
    ["drive_ms", "1", "15", "220623092146"],
    ["vdisk_r_mb", "100", "500", "220623092541"],
    ["vdisk_r_io", "10", "50", "220623092541"],
    ["vdisk_r_ms", "5", "10", "220623092541"],
    ["vdisk_w_mb", "50", "100", "220623092541"],
    ["vdisk_w_io", "10", "50", "220623092541"],
    ["vdisk_w_ms", "20", "50", "220623092541"],
    ["mdisk_r_mb", "200", "1000", "220623092541"],
    ["mdisk_r_io", "0", "0", "220623092541"],
    ["mdisk_r_ms", "0", "0", "220623092541"],
    ["mdisk_w_mb", "300", "500", "220623092541"],
    ["mdisk_w_io", "0", "0", "220623092541"],
    ["mdisk_w_ms", "0", "0", "220623092541"],
    ["drive_r_mb", "39", "372", "220623092516"],
    ["drive_r_io", "155", "1480", "220623092516"],
    ["drive_r_ms", "1", "15", "220623092146"],
    ["drive_w_mb", "0", "0", "220623092541"],
    ["drive_w_io", "0", "5", "220623092516"],
    ["drive_w_ms", "0", "4", "220623092416"],
    ["power_w", "263", "263", "220623092541"],
    ["temp_c", "27", "27", "220623092541"],
    ["temp_f", "80", "80", "220623092541"],
    ["iplink_mb", "0", "0", "220623092541"],
    ["iplink_io", "0", "0", "220623092541"],
    ["iplink_comp_mb", "0", "0", "220623092541"],
    ["cloud_up_mb", "0", "0", "220623092541"],
    ["cloud_up_ms", "0", "0", "220623092541"],
    ["cloud_down_mb", "0", "0", "220623092541"],
    ["cloud_down_ms", "0", "0", "220623092541"],
    ["iser_mb", "0", "0", "220623092541"],
    ["iser_io", "0", "0", "220623092541"],
]

TEST_SECTION = IBMSystemStats(
    cpu_pc=91,
    total_cache_pc=2,
    write_cache_pc=0,
    disks={
        "VDisks": {
            "r_mb": 100,
            "r_io": 10,
            "r_ms": 5,
            "w_mb": 50,
            "w_io": 10,
            "w_ms": 20,
        },
        "MDisks": {
            "r_mb": 200,
            "r_io": 0,
            "r_ms": 0,
            "w_mb": 300,
            "w_io": 0,
            "w_ms": 0,
        },
        "Drives": {"r_mb": 39, "r_io": 155, "r_ms": 1, "w_mb": 0, "w_io": 0, "w_ms": 0},
    },
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            TEST_INFO,
            TEST_SECTION,
            id="parse_ibm_svc_systemstats",
        ),
        pytest.param(
            [
                ["mdisk_r_mb", "200.1", "1000", "220623092541"],
                ["vdisk_r_ms", "5.00", "10", "220623092541"],
                ["drive_w_io", "0.000", "5", "220623092516"],
            ],
            IBMSystemStats(
                cpu_pc=None,
                total_cache_pc=None,
                write_cache_pc=None,
                disks={
                    "MDisks": {
                        "r_mb": 200.1,
                    },
                    "VDisks": {
                        "r_ms": 5.0,
                    },
                    "Drives": {
                        "w_io": 0.0,
                    },
                },
            ),
            id="parse_ibm_svc_systemstats_floats",
        ),
    ],
)
def test_ibm_svc_systemstats_parse(
    string_table: StringTable,
    expected_section: IBMSystemStats,
) -> None:
    result = ibm_svc_systemstats_parse(string_table)
    assert result == expected_section


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        pytest.param(
            TEST_SECTION,
            [Service(item="VDisks"), Service(item="MDisks"), Service(item="Drives")],
            id="diskio",
        )
    ],
)
def test_discovery_ibm_svc_systemstats_disks(
    section: IBMSystemStats,
    expected_discovery: Sequence[Service],
) -> None:
    result = list(discovery_ibm_svc_systemstats_disks(section))
    assert result == expected_discovery


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            TEST_SECTION,
            "VDisks",
            [
                Result(state=State.OK, summary="105 MB/s read, 52.4 MB/s write"),
                Metric("read", 104857600.0),
                Metric("write", 52428800.0),
            ],
            id="diskio",
        ),
        pytest.param(
            TEST_SECTION,
            "unknown_item",
            [],
            id="diskio_no_item",
        ),
    ],
)
def test_check_ibm_svc_systemstats_diskio(
    section: IBMSystemStats,
    item: str,
    expected_result: Sequence[CheckResult],
) -> None:
    assert list(check_ibm_svc_systemstats_diskio(item=item, section=section)) == list(
        expected_result
    )


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            TEST_SECTION,
            "VDisks",
            [
                Result(state=State.OK, summary="10 IO/s read, 10 IO/s write"),
                Metric("read", 10.0),
                Metric("write", 10.0),
            ],
            id="iops",
        ),
        pytest.param(
            TEST_SECTION,
            "unknown_item",
            [],
            id="iops_no_item",
        ),
    ],
)
def test_check_ibm_svc_systemstats_iops(
    section: IBMSystemStats,
    item: str,
    expected_result: Sequence[CheckResult],
) -> None:
    assert list(check_ibm_svc_systemstats_iops(item=item, section=section)) == list(expected_result)


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        pytest.param(
            TEST_SECTION,
            "VDisks",
            {},
            [
                Result(state=State.OK, summary="read latency: 5 ms"),
                Metric("read_latency", 5.0),
                Result(state=State.OK, summary="write latency: 20 ms"),
                Metric("write_latency", 20.0),
            ],
            id="disk_latency",
        ),
        pytest.param(
            TEST_SECTION,
            "VDisks",
            {"read": (4.0, 10.0), "write": (25.0, 50.0)},
            [
                Result(
                    state=State.WARN,
                    summary="read latency: 5 ms (warn/crit at 4.0 ms/10.0 ms)",
                ),
                Metric("read_latency", 5.0, levels=(4.0, 10.0)),
                Result(state=State.OK, summary="write latency: 20 ms"),
                Metric("write_latency", 20.0, levels=(25.0, 50.0)),
            ],
            id="disk_latency_params",
        ),
        pytest.param(
            TEST_SECTION,
            "unknown_item",
            {},
            [],
            id="disk_latency_no_item",
        ),
    ],
)
def test_check_ibm_svc_systemstats_disk_latency(
    section: IBMSystemStats,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[CheckResult],
) -> None:
    assert list(
        check_ibm_svc_systemstats_disk_latency(item=item, params=params, section=section)
    ) == list(expected_result)


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        pytest.param(
            TEST_SECTION,
            [Service()],
            id="cpu",
        )
    ],
)
def test_discovery_ibm_svc_systemstats_cpu(
    section: IBMSystemStats,
    expected_discovery: Sequence[Service],
) -> None:
    result = list(discovery_ibm_svc_systemstats_cpu(section))
    assert result == expected_discovery


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            TEST_SECTION,
            {"util": (10.0, 25.0)},
            [
                Result(state=State.CRIT, summary="Total CPU: 91.00% (warn/crit at 10.00%/25.00%)"),
                Metric("util", 91.0, levels=(10.0, 25.0), boundaries=(0.0, None)),
            ],
            id="cpu",
        ),
        pytest.param(
            TEST_SECTION,
            {"util": (90.0, 95.0)},
            [
                Result(state=State.WARN, summary="Total CPU: 91.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 91.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="cpu_default_params",
        ),
        pytest.param(
            IBMSystemStats(
                cpu_pc=None,
                total_cache_pc=2,
                write_cache_pc=None,
                disks={},
            ),
            {"util": (90.0, 95.0)},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="value cpu_pc not found in agent output",
                )
            ],
            id="cpu_no_cpu_pc",
        ),
    ],
)
def test_check_ibm_svc_systemstats_cpu(
    section: IBMSystemStats,
    params: Mapping[str, Any],
    expected_result: Sequence[CheckResult],
) -> None:
    assert list(check_ibm_svc_systemstats_cpu(params=params, section=section)) == list(
        expected_result
    )


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        pytest.param(
            TEST_SECTION,
            [Service()],
            id="disk_latency",
        )
    ],
)
def test_discovery_ibm_svc_systemstats_cache(
    section: IBMSystemStats,
    expected_discovery: Sequence[Service],
) -> None:
    result = list(discovery_ibm_svc_systemstats_cache(section))
    assert result == expected_discovery


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            TEST_SECTION,
            [
                Result(
                    state=State.OK, summary="Write cache usage is 0 %, total cache usage is 2 %"
                ),
                Metric("write_cache_pc", 0.0, boundaries=(0.0, 100.0)),
                Metric("total_cache_pc", 2.0, boundaries=(0.0, 100.0)),
            ],
            id="cpu",
        ),
        pytest.param(
            IBMSystemStats(
                cpu_pc=91,
                total_cache_pc=None,
                write_cache_pc=None,
                disks={},
            ),
            [Result(state=State.UNKNOWN, summary="value total_cache_pc not found in agent output")],
            id="cpu_no_total_cache_pc",
        ),
        pytest.param(
            IBMSystemStats(
                cpu_pc=91,
                total_cache_pc=2,
                write_cache_pc=None,
                disks={},
            ),
            [Result(state=State.UNKNOWN, summary="value write_cache_pc not found in agent output")],
            id="cpu_no_write_cache_pc",
        ),
    ],
)
def test_check_ibm_svc_systemstats_cache(
    section: IBMSystemStats,
    expected_result: Sequence[CheckResult],
) -> None:
    assert list(check_ibm_svc_systemstats_cache(section=section)) == list(expected_result)
