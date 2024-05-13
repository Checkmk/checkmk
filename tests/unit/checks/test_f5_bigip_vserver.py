#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from .checktestlib import Check


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
    info: list[Sequence[str]],
    item: str,
    expected_item_data: Mapping[str, str | Sequence[float]],
) -> None:
    parsed = Check("f5_bigip_vserver").run_parse(info)
    assert isinstance(parsed, dict)
    assert sorted(parsed[item].items()) == sorted(expected_item_data.items())
