#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.ibm_svc_array import (
    check_ibm_svc_array,
    discover_ibm_svc_array,
    parse_ibm_svc_array,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "27",
                    "SSD_mdisk27",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "28",
                    "SSD_mdisk28",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "29",
                    "SSD_mdisk0",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "30",
                    "SSD_mdisk1",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
            ],
            [("27", {}), ("28", {}), ("29", {}), ("30", {})],
        ),
    ],
)
def test_discover_ibm_svc_array(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ibm_svc_array check."""
    parsed = parse_ibm_svc_array(string_table)
    result = list(discover_ibm_svc_array(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "27",
            {},
            [
                [
                    "27",
                    "SSD_mdisk27",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "28",
                    "SSD_mdisk28",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "29",
                    "SSD_mdisk0",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "30",
                    "SSD_mdisk1",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
            ],
            [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd")],
        ),
        (
            "28",
            {},
            [
                [
                    "27",
                    "SSD_mdisk27",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "28",
                    "SSD_mdisk28",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "29",
                    "SSD_mdisk0",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "30",
                    "SSD_mdisk1",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
            ],
            [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd")],
        ),
        (
            "29",
            {},
            [
                [
                    "27",
                    "SSD_mdisk27",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "28",
                    "SSD_mdisk28",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "29",
                    "SSD_mdisk0",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "30",
                    "SSD_mdisk1",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
            ],
            [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd")],
        ),
        (
            "30",
            {},
            [
                [
                    "27",
                    "SSD_mdisk27",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "28",
                    "SSD_mdisk28",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "29",
                    "SSD_mdisk0",
                    "online",
                    "1",
                    "POOL_0_V7000_RZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
                [
                    "30",
                    "SSD_mdisk1",
                    "online",
                    "2",
                    "POOL_1_V7000_BRZ",
                    "372.1GB",
                    "online",
                    "raid1",
                    "1",
                    "256",
                    "generic_ssd",
                ],
            ],
            [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd")],
        ),
    ],
)
def test_check_ibm_svc_array(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ibm_svc_array check."""
    parsed = parse_ibm_svc_array(string_table)
    result = list(check_ibm_svc_array(item, params, parsed))
    assert result == expected_results
