#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.prism.agent_based.prism_cluster_mem import (
    check_prism_cluster_mem,
    discovery_prism_cluster_mem,
)

SECTION = {
    "stats": {
        "controller_avg_io_latency_usecs": "1246",
        "controller_avg_read_io_latency_usecs": "321",
        "controller_avg_read_io_size_kbytes": "44",
        "controller_avg_write_io_latency_usecs": "1406",
        "controller_avg_write_io_size_kbytes": "81",
        "controller_io_bandwidth_kBps": "33307",
        "controller_num_io": "13153",
        "controller_num_iops": "438",
        "controller_num_random_io": "-1",
        "controller_num_read_io": "1943",
        "controller_num_read_iops": "64",
        "controller_num_seq_io": "-1",
        "controller_num_write_io": "11210",
        "controller_num_write_iops": "373",
        "controller_random_io_ppm": "-1",
        "controller_read_io_bandwidth_kBps": "2869",
        "controller_read_io_ppm": "147722",
        "controller_seq_io_ppm": "-1",
        "controller_timespan_usecs": "30000000",
        "controller_write_io_bandwidth_kBps": "30437",
        "controller_write_io_ppm": "852277",
        "hypervisor_avg_io_latency_usecs": "0",
        "hypervisor_avg_read_io_latency_usecs": "0",
        "hypervisor_avg_write_io_latency_usecs": "0",
        "hypervisor_cpu_usage_ppm": "135137",
        "hypervisor_io_bandwidth_kBps": "0",
        "hypervisor_memory_usage_ppm": "737407",
        "hypervisor_read_io_bandwidth_kBps": "0",
        "hypervisor_timespan_usecs": "29824927",
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
            id="The check is discovered if the cluster provides stats data.",
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
    assert list(discovery_prism_cluster_mem(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {"levels": (70.0, 80.0)},
            SECTION,
            [
                Result(
                    state=State.WARN,
                    summary="Total Memory Usage: 73.74% (warn/crit at 70.00%/80.00%)",
                ),
                Metric(
                    "prism_cluster_mem_used", 73.7407, levels=(70.0, 80.0), boundaries=(0.0, 100.0)
                ),
            ],
            id="If the cluster memory usage is outside the warning threshold, the check result is WARN.",
        ),
    ],
)
def test_check_prism_cluster_mem(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_cluster_mem(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
