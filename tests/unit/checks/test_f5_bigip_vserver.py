#!/usr/bin/env python3

import pytest

from tests.testlib import Check


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
def test_wmi_cpu_load_discovery(info, item, expected_item_data):
    check = Check("f5_bigip_vserver")
    assert sorted(check.run_parse(info)[item].items()) == sorted(expected_item_data.items())
