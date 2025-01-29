#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.prism.agent_based.prism_vm_stats import (
    check_prism_vm_stats,
    check_prism_vm_stats_cpu,
    check_prism_vm_stats_mem,
    discovery_prism_vm_stats,
    discovery_prism_vm_stats_cpu,
    discovery_prism_vm_stats_mem,
)

SECTION = {
    "hostName": "SRV-AHV-01",
    "powerState": "on",
    "stats": {
        "controller_avg_io_latency_usecs": "875",
        "controller_avg_read_io_latency_usecs": "210",
        "controller_avg_read_io_size_kbytes": "32",
        "controller_avg_write_io_latency_usecs": "878",
        "controller_avg_write_io_size_kbytes": "15",
        "guest.memory_swapped_in_bytes": "307200",
        "guest.memory_swapped_out_bytes": "0",
        "guest.memory_usage_bytes": "13128548352",
        "guest.memory_usage_ppm": "764369",
        "hypervisor.cpu_ready_time_ppm": "89",
        "hypervisor_cpu_usage_ppm": "90786",
    },
    "vmName": "SRV-APP-03",
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
def test_discovery_prism_vm_stats(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_vm_stats(section)) == expected_discovery_result
    assert list(discovery_prism_vm_stats_cpu(section)) == expected_discovery_result
    assert list(discovery_prism_vm_stats_mem(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["section", "expected_check_result"],
    [
        pytest.param(
            SECTION,
            [
                Result(state=State.OK, summary="is 31.2 KiB read and 14.6 KiB write"),
                Metric("avg_latency", 875.0),
                Metric("avg_read_lat", 210.0),
                Metric("avg_write_lat", 878.0),
                Metric("avg_read_bytes", 32000.0),
                Metric("avg_write_bytes", 15000.0),
            ],
            id="If the disk capacity are inside the filesystem levels, the check result is OK.",
        ),
    ],
)
def test_check_prism_vm_stats(
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_vm_stats(
                section=section,
            )
        )
        == expected_check_result
    )


@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {"levels": (80.0, 90.0), "levels_rdy": (5.0, 10.0)},
            SECTION,
            [
                Result(state=State.OK, summary="CPU usage: 9.08%"),
                Metric("cpu_usage", 9.0786, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="CPU ready: <0.01%"),
                Metric("cpu_ready", 0.0089, levels=(5.0, 10.0), boundaries=(0.0, 100.0)),
            ],
            id="If the disk capacity are inside the filesystem levels, the check result is OK.",
        ),
    ],
)
def test_check_prism_vm_stats_cpu(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_vm_stats_cpu(
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
                Result(state=State.OK, summary="Usage: 76.44% - 12.2 GiB of 16.0 GiB"),
                Metric(
                    "mem_used",
                    13128548352.0,
                    levels=(13740534586.400002, 15458101409.7),
                    boundaries=(0.0, 17175668233.0),
                ),
                Metric("mem_total", 17175668233.0),
            ],
            id="If the disk capacity are inside the filesystem levels, the check result is OK.",
        ),
    ],
)
def test_check_prism_vm_stats_mem(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_vm_stats_mem(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
