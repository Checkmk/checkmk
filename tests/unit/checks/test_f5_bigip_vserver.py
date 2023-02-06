#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import Check

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.mark.parametrize(
    "info, item, expected_item_data",
    [
        (
            [
                [
                    "/path/to-1",
                    "1",
                    "1",
                    "The virtual server is available",
                    "1.2.3.4",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                ],
            ],
            "/path/to-1",
            {
                "connections": [9],
                "connections_duration_max": [0.002],
                "connections_duration_mean": [0.003],
                "connections_duration_min": [0.001],
                "connections_rate": [8],
                "detail": "The virtual server is available",
                "enabled": "1",
                "if_in_octets": [6],
                "if_in_pkts": [4],
                "if_out_octets": [7],
                "if_out_pkts": [5],
                "ip_address": "-",
                "packet_velocity_asic": [10],
                "status": "1",
            },
        ),
        (
            [
                [
                    "/path/to-1",
                    "1",
                    "1",
                    "The virtual server is available",
                    "\n\x10˂",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                ],
            ],
            "/path/to-1",
            {
                "connections": [9],
                "connections_duration_max": [0.002],
                "connections_duration_mean": [0.003],
                "connections_duration_min": [0.001],
                "connections_rate": [8],
                "detail": "The virtual server is available",
                "enabled": "1",
                "if_in_octets": [6],
                "if_in_pkts": [4],
                "if_out_octets": [7],
                "if_out_pkts": [5],
                "ip_address": "-",
                "packet_velocity_asic": [10],
                "status": "1",
            },
        ),
    ],
)
def test_f5_bigip_vserver_parsing(
    info: Sequence[Sequence[str]],
    item: str,
    expected_item_data: Mapping[str, str | Sequence[float]],
) -> None:
    check = Check("f5_bigip_vserver")
    assert sorted(check.run_parse(info)[item].items()) == sorted(expected_item_data.items())


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, item, params, expected_check_result",
    [
        pytest.param(
            [
                [
                    "/path/to-1",
                    "1",
                    "1",
                    "The virtual server is available",
                    "1.2.3.4",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                ],
            ],
            "/path/to-1",
            {"connections": (10, 20)},
            [
                (0, "Virtual Server with IP - is enabled"),
                (0, "State is up and available, Detail: The virtual server is available"),
                (
                    0,
                    "Client connections: 9",
                    [
                        ("connections", 9),
                        ("connections_duration_max", 0.002),
                        ("connections_duration_mean", 0.003),
                        ("connections_duration_min", 0.001),
                        ("connections_rate", 0.0),
                        ("if_in_octets", 0.0),
                        ("if_in_pkts", 0.0),
                        ("if_out_octets", 0.0),
                        ("if_out_pkts", 0.0),
                        ("if_total_octets", 0.0),
                        ("if_total_pkts", 0.0),
                        ("packet_velocity_asic", 0.0),
                    ],
                ),
                (0, "Connections rate: 0.00/sec"),
            ],
            id="The number of connections is below the WARN/CRIT levels, so the check state is OK.",
        ),
        pytest.param(
            [
                [
                    "/path/to-1",
                    "1",
                    "1",
                    "The virtual server is available",
                    "1.2.3.4",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "15",
                    "10",
                ],
            ],
            "/path/to-1",
            {"connections": (10, 20)},
            [
                (0, "Virtual Server with IP - is enabled"),
                (0, "State is up and available, Detail: The virtual server is available"),
                (
                    1,
                    "Client connections: 15",
                    [
                        ("connections", 15),
                        ("connections_duration_max", 0.002),
                        ("connections_duration_mean", 0.003),
                        ("connections_duration_min", 0.001),
                        ("connections_rate", 0.0),
                        ("if_in_octets", 0.0),
                        ("if_in_pkts", 0.0),
                        ("if_out_octets", 0.0),
                        ("if_out_pkts", 0.0),
                        ("if_total_octets", 0.0),
                        ("if_total_pkts", 0.0),
                        ("packet_velocity_asic", 0.0),
                    ],
                ),
                (0, "Connections rate: 0.00/sec"),
            ],
            id="The number of connections is above the WARN level, so the check state is WARN.",
        ),
        pytest.param(
            [
                [
                    "/path/to-1",
                    "1",
                    "1",
                    "The virtual server is available",
                    "1.2.3.4",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "25",
                    "10",
                ],
            ],
            "/path/to-1",
            {"connections": (10, 20)},
            [
                (0, "Virtual Server with IP - is enabled"),
                (0, "State is up and available, Detail: The virtual server is available"),
                (
                    2,
                    "Client connections: 25",
                    [
                        ("connections", 25),
                        ("connections_duration_max", 0.002),
                        ("connections_duration_mean", 0.003),
                        ("connections_duration_min", 0.001),
                        ("connections_rate", 0.0),
                        ("if_in_octets", 0.0),
                        ("if_in_pkts", 0.0),
                        ("if_out_octets", 0.0),
                        ("if_out_pkts", 0.0),
                        ("if_total_octets", 0.0),
                        ("if_total_pkts", 0.0),
                        ("packet_velocity_asic", 0.0),
                    ],
                ),
                (0, "Connections rate: 0.00/sec"),
            ],
            id="The number of connections is above the CRIT level, so the check state is CRIT.",
        ),
    ],
)
def test_f5_bigip_vserver_check(
    string_table: StringTable,
    item: str,
    params: Mapping[str, tuple[int, int]],
    expected_check_result: Sequence[Any],
) -> None:
    check = Check("f5_bigip_vserver")
    assert (
        list(check.run_check(item, params, check.run_parse(string_table))) == expected_check_result
    )
