#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.prism.agent_based.prism_host_stats import (
    check_prism_host_stats,
    check_prism_host_stats_cpu,
    check_prism_host_stats_mem,
    discovery_prism_host_stats,
    discovery_prism_host_stats_cpu,
    discovery_prism_host_stats_mem,
)

SECTION = {
    "cpu_capacity_in_hz": 51200000000,
    "cpu_frequency_in_hz": 3200000000,
    "memory_capacity_in_bytes": 404078198784,
    "num_cpu_cores": 16,
    "num_cpu_sockets": 2,
    "num_cpu_threads": 32,
    "num_vms": 4,
    "state": "NORMAL",
    "stats": {
        "controller_avg_io_latency_usecs": "1473",
        "controller_avg_read_io_latency_usecs": "1519",
        "controller_avg_read_io_size_kbytes": "46",
        "controller_avg_write_io_latency_usecs": "1473",
        "controller_avg_write_io_size_kbytes": "11",
        "controller_io_bandwidth_kBps": "879",
        "controller_num_io": "1512",
        "controller_num_iops": "75",
        "controller_num_random_io": "0",
        "controller_num_read_io": "2",
        "controller_num_read_iops": "0",
        "controller_num_seq_io": "-1",
        "controller_num_write_io": "1510",
        "controller_num_write_iops": "75",
        "controller_random_io_ppm": "-1",
        "controller_read_io_bandwidth_kBps": "4",
        "controller_read_io_ppm": "1322",
        "controller_seq_io_ppm": "-1",
        "controller_timespan_usecs": "20000000",
        "controller_total_io_size_kbytes": "17584",
        "controller_total_io_time_usecs": "2227642",
        "controller_total_read_io_size_kbytes": "92",
        "controller_total_read_io_time_usecs": "3039",
        "controller_total_transformed_usage_bytes": "-1",
        "controller_write_io_bandwidth_kBps": "874",
        "controller_write_io_ppm": "998677",
        "hypervisor_avg_io_latency_usecs": "0",
        "hypervisor_avg_read_io_latency_usecs": "0",
        "hypervisor_avg_write_io_latency_usecs": "0",
        "hypervisor_cpu_usage_ppm": "172609",
        "hypervisor_io_bandwidth_kBps": "0",
        "hypervisor_memory_usage_ppm": "247726",
        "hypervisor_num_io": "0",
        "hypervisor_num_iops": "0",
        "hypervisor_num_read_io": "0",
        "hypervisor_num_read_iops": "0",
        "hypervisor_num_received_bytes": "20990113397570",
        "hypervisor_num_transmitted_bytes": "24316319197591",
        "hypervisor_num_write_io": "0",
        "hypervisor_num_write_iops": "0",
        "hypervisor_read_io_bandwidth_kBps": "0",
        "hypervisor_timespan_usecs": "30194001",
        "hypervisor_total_io_size_kbytes": "0",
        "hypervisor_total_io_time_usecs": "0",
        "hypervisor_total_read_io_size_kbytes": "0",
        "hypervisor_total_read_io_time_usecs": "0",
        "hypervisor_write_io_bandwidth_kBps": "0",
    },
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(),
            ],
            id="The check is discovered if the host provides stats data.",
        ),
        pytest.param(
            {},
            [],
            id="If there is no stats data, nothing is discovered.",
        ),
    ],
)
def test_discovery_prism_host_stats(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_host_stats(section)) == expected_discovery_result
    assert list(discovery_prism_host_stats_cpu(section)) == expected_discovery_result
    assert list(discovery_prism_host_stats_mem(section)) == expected_discovery_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["section", "expected_check_result"],
    [
        pytest.param(
            SECTION,
            [
                Result(state=State.OK, summary="is 44.9 KiB read and 10.7 KiB write"),
                Metric("avg_latency", 1473.0),
                Metric("avg_read_lat", 1519.0),
                Metric("avg_write_lat", 1473.0),
                Metric("avg_read_bytes", 46.0),
                Metric("avg_write_bytes", 11.0),
            ],
            id="If the disk capacity are inside the filesystem levels, the check result is OK.",
        ),
    ],
)
def test_check_prism_host_stats(
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_host_stats(
                section=section,
            )
        )
        == expected_check_result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {},
            SECTION,
            [
                Result(state=State.OK, summary="Total CPU: 17.26%"),
                Metric("util", 17.2609, boundaries=(0.0, None)),
                Result(state=State.OK, notice="8.84 GHz/51.2 GHz"),
                Result(state=State.OK, notice="Sockets: 2"),
                Result(state=State.OK, notice="Cores/socket: 8"),
                Result(state=State.OK, notice="Threads: 32"),
            ],
            id="If the disk capacity are inside the filesystem levels, the check result is OK.",
        ),
    ],
)
def test_check_prism_host_stats_cpu(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_host_stats_cpu(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )


@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {"levels_upper": (80.0, 90.0)},
            SECTION,
            [
                Result(state=State.OK, summary="Usage: 24.77% - 93.2 GiB of 376 GiB"),
                Metric(
                    "mem_used",
                    100100675871.9652,
                    levels=(323262559027.2, 363670378905.60004),
                    boundaries=(0.0, 404078198784.0),
                ),
                Metric("mem_total", 404078198784.0),
            ],
            id="If the disk capacity are inside the filesystem levels, the check result is OK.",
        ),
    ],
)
def test_check_prism_host_stats_mem(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_host_stats_mem(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
