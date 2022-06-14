#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

from cmk.base.plugins.agent_based import netapp_api_cpu, netapp_api_vf_stats
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    State,
)

SECTION_NETAPP_API_VF_STATS = {
    "vfiler0": {
        "vfiler": "vfiler0",
        "instance_uuid": "",
        "node_uuid": "",
        "vfiler_cpu_busy": "774093444785907",
        "vfiler_net_data_sent": "11257211",
        "vfiler_read_ops": "16501039",
        "vfiler_cpu_busy_base": "48126443476302566",
        "process_name": "",
        "vfiler_write_bytes": "16990138",
        "node_name": "",
        "instance_name": "vfiler0",
        "vfiler_write_ops": "35590594",
        "vfiler_net_data_recv": "2622909",
        "vfiler_read_bytes": "245287066",
        "vfiler_misc_ops": "2403260943",
    }
}

SECTION_NETAPP_API_CPU: netapp_api_cpu.CPUSection = {
    "7mode": {"num_processors": "2", "cpu_busy": "153993540928"}
}


@pytest.mark.parametrize(
    "params, exp_res",
    [
        (
            {"levels": (90.0, 95.0)},
            [
                Result(state=State.OK, summary="Total CPU: 0%"),
                Metric("util", 0.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
                Result(state=State.OK, notice="Number of processors: 2"),
            ],
        ),
        (
            {
                "levels": (0, 95.0),
                "average": 5,
            },
            [
                Metric("util", 0.0, levels=(0.0, 95.0), boundaries=(0.0, 100.0)),
                Result(
                    state=State.WARN,
                    summary="Total CPU (5 min average): 0% (warn/crit at 0%/95.00%)",
                    details="Total CPU (5 min average): 0% (warn/crit at 0%/95.00%)",
                ),
                Metric("util_average", 0.0, levels=(0.0, 95.0), boundaries=(0.0, None)),
                Result(state=State.OK, notice="Number of processors: 2"),
            ],
        ),
    ],
)
def test_check_netapp_api_vf_stats(params, exp_res) -> None:
    now = 0.0
    value_store: dict[str, Any] = {}
    # initialize counters
    with pytest.raises(IgnoreResultsError):
        list(
            netapp_api_vf_stats._check_netapp_api_vf_stats(
                "vfiler0",
                params,
                SECTION_NETAPP_API_VF_STATS,
                SECTION_NETAPP_API_CPU,
                now=now,
                value_store=value_store,
            )
        )
    assert (
        list(
            netapp_api_vf_stats._check_netapp_api_vf_stats(
                "vfiler0",
                params,
                SECTION_NETAPP_API_VF_STATS,
                SECTION_NETAPP_API_CPU,
                now=now + 0.0001,
                value_store=value_store,
            )
        )
        == exp_res
    )


def test_check_netapp_api_vf_stats_traffic() -> None:
    now = 0.0
    value_store: dict[str, Any] = {}
    # initialize counters
    assert (
        list(
            netapp_api_vf_stats._check_netapp_api_vf_stats_traffic(
                "vfiler0",
                SECTION_NETAPP_API_VF_STATS,
                now=now,
                value_store=value_store,
            )
        )
        == []
    )
    assert list(
        netapp_api_vf_stats._check_netapp_api_vf_stats_traffic(
            "vfiler0",
            SECTION_NETAPP_API_VF_STATS,
            now=now + 0.000001,
            value_store=value_store,
        )
    ) == [
        Result(
            state=State.OK, summary="Read operations: 0.00/s", details="Read operations: 0.00/s"
        ),
        Metric("read_ops", 0.0),
        Result(
            state=State.OK, summary="Write operations: 0.00/s", details="Write operations: 0.00/s"
        ),
        Metric("write_ops", 0.0),
        Result(
            state=State.OK,
            summary="Received network data: 0.00 B/s",
            details="Received network data: 0.00 B/s",
        ),
        Metric("net_data_recv", 0.0),
        Result(
            state=State.OK,
            summary="Sent network data: 0.00 B/s",
            details="Sent network data: 0.00 B/s",
        ),
        Metric("net_data_sent", 0.0),
        Result(
            state=State.OK, summary="Read throughput: 0.00 B/s", details="Read throughput: 0.00 B/s"
        ),
        Metric("read_bytes", 0.0),
        Result(
            state=State.OK,
            summary="Write throughput: 0.00 B/s",
            details="Write throughput: 0.00 B/s",
        ),
        Metric("write_bytes", 0.0),
    ]
