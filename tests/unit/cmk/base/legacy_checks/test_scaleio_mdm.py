#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.scaleio_mdm import (
    check_scaleio_mdm,
    discover_scaleio_mdm,
    parse_scaleio_mdm,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["Cluster:"],
                ["Name: tuc", " Mode: 5_node", " State: Normal", " Active: 5/5", " Replicas: 3/3"],
                ["Virtual IPs: 192.168.50.21", " 192.168.51.21", " 123.456.78.99"],
                ["Master MDM:"],
                ["Name: Manager1", " ID: 0x0000000000000001"],
                [
                    "IPs: 192.168.50.1",
                    " 192.168.51.1",
                    " Management IPs: 123.456.78.91",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Version: 2.5.0"],
                ["Slave MDMs:"],
                ["Name: Manager2", " ID: 0x0000000000000002"],
                [
                    "IPs: 192.168.50.2",
                    " 192.168.51.2",
                    " Management IPs: 123.456.78.92",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Normal", " Version: 2.5.0"],
                ["Name: Manager3", " ID: 0x0000000000000003"],
                [
                    "IPs: 192.168.50.3",
                    " 192.168.51.3",
                    " Management IPs: 123.456.78.93",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Degraded", " Version: 2.5.0"],
                ["Name: Manager4", " ID: 0x0000000000000004"],
                [
                    "IPs: 192.168.50.4",
                    " 192.168.51.4",
                    " Management IPs: 123.456.78.94",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Not synchronized", " Version: 2.5.0"],
                ["Name: Manager5", " ID: 0x0000000000000005"],
                [
                    "IPs: 192.168.50.5",
                    " 192.168.51.5",
                    " Management IPs: 123.456.78.95",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Error", " Version: 2.5.0"],
                ["Name: Manager6", " ID: 0x0000000000000006"],
                [
                    "IPs: 192.168.50.6",
                    " 192.168.51.6",
                    " Management IPs: 123.456.78.96",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Disconnected", " Version: 2.5.0"],
                ["Standby MDMs:"],
                ["Name: Standby1", " ID: 0x00000000000007", " Manager"],
                [
                    "IPs: 192.168.50.7",
                    " 192.168.51.7",
                    " Management IPs: 123.456.78.97",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Tie-Breakers:"],
                ["Name: TB1", " ID: 0xtb00000000000008"],
                ["IPs: 192.168.50.3", " 192.168.51.3", " Port: 9011"],
                ["Status: Normal", " Version: 2.5.0"],
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_scaleio_mdm(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for scaleio_mdm check."""
    parsed = parse_scaleio_mdm(string_table)
    result = list(discover_scaleio_mdm(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                ["Cluster:"],
                ["Name: tuc", " Mode: 5_node", " State: Normal", " Active: 5/5", " Replicas: 3/3"],
                ["Virtual IPs: 192.168.50.21", " 192.168.51.21", " 123.456.78.99"],
                ["Master MDM:"],
                ["Name: Manager1", " ID: 0x0000000000000001"],
                [
                    "IPs: 192.168.50.1",
                    " 192.168.51.1",
                    " Management IPs: 123.456.78.91",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Version: 2.5.0"],
                ["Slave MDMs:"],
                ["Name: Manager2", " ID: 0x0000000000000002"],
                [
                    "IPs: 192.168.50.2",
                    " 192.168.51.2",
                    " Management IPs: 123.456.78.92",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Normal", " Version: 2.5.0"],
                ["Name: Manager3", " ID: 0x0000000000000003"],
                [
                    "IPs: 192.168.50.3",
                    " 192.168.51.3",
                    " Management IPs: 123.456.78.93",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Degraded", " Version: 2.5.0"],
                ["Name: Manager4", " ID: 0x0000000000000004"],
                [
                    "IPs: 192.168.50.4",
                    " 192.168.51.4",
                    " Management IPs: 123.456.78.94",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Not synchronized", " Version: 2.5.0"],
                ["Name: Manager5", " ID: 0x0000000000000005"],
                [
                    "IPs: 192.168.50.5",
                    " 192.168.51.5",
                    " Management IPs: 123.456.78.95",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Error", " Version: 2.5.0"],
                ["Name: Manager6", " ID: 0x0000000000000006"],
                [
                    "IPs: 192.168.50.6",
                    " 192.168.51.6",
                    " Management IPs: 123.456.78.96",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Status: Disconnected", " Version: 2.5.0"],
                ["Standby MDMs:"],
                ["Name: Standby1", " ID: 0x00000000000007", " Manager"],
                [
                    "IPs: 192.168.50.7",
                    " 192.168.51.7",
                    " Management IPs: 123.456.78.97",
                    " Port: 9011",
                    " Virtual IP interfaces: eth1",
                    " eth2",
                    " eth0",
                ],
                ["Tie-Breakers:"],
                ["Name: TB1", " ID: 0xtb00000000000008"],
                ["IPs: 192.168.50.3", " 192.168.51.3", " Port: 9011"],
                ["Status: Normal", " Version: 2.5.0"],
            ],
            [
                (0, "Mode: 5_node, State: Normal"),
                (0, "Active: 5/5, Replicas: 3/3"),
                (0, "Master MDM: Manager1"),
                (2, "Slave MDMs: Manager2, Manager3, Manager4, Manager5, Manager6"),
                (0, "Tie-Breakers: TB1"),
                (0, "Standby MDMs: Standby1"),
            ],
        ),
    ],
)
def test_check_scaleio_mdm(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for scaleio_mdm check."""
    parsed = parse_scaleio_mdm(string_table)
    result = list(check_scaleio_mdm(item, params, parsed))
    assert result == expected_results
