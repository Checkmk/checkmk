#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.ibm_svc.agent_based.ibm_svc_portfc import (
    check_ibm_svc_portfc,
    discover_ibm_svc_portfc,
    parse_ibm_svc_portfc,
)

STRING_TABLE: StringTable = [
    [
        "0",
        "1",
        "1",
        "fc",
        "8Gb",
        "1",
        "node1",
        "5005076803042126",
        "030400",
        "active",
        "switch",
    ],
    [
        "1",
        "2",
        "2",
        "fc",
        "8Gb",
        "1",
        "node1",
        "5005076803082126",
        "040400",
        "active",
        "switch",
        "local_partner",
    ],
    [
        "2",
        "3",
        "3",
        "fc",
        "N/A",
        "1",
        "node1",
        "50050768030C2126",
        "000000",
        "inactive_unconfigured",
        "none",
    ],
    [
        "3",
        "4",
        "4",
        "fc",
        "N/A",
        "1",
        "node1",
        "5005076803102126",
        "000000",
        "inactive_unconfigured",
        "none",
    ],
    [
        "8",
        "1",
        "1",
        "fc",
        "8Gb",
        "2",
        "node2",
        "5005076803042127",
        "030500",
        "active",
        "switch",
        "local_partner",
    ],
    [
        "9",
        "2",
        "2",
        "fc",
        "8Gb",
        "2",
        "node2",
        "5005076803082127",
        "040500",
        "active",
        "switch",
    ],
    [
        "10",
        "3",
        "3",
        "fc",
        "N/A",
        "2",
        "node2",
        "50050768030C2127",
        "000000",
        "inactive_unconfigured",
        "none",
    ],
    [
        "11",
        "4",
        "4",
        "fc",
        "N/A",
        "2",
        "node2",
        "5005076803102127",
        "000000",
        "inactive_unconfigured",
        "none",
        "local_partner",
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            STRING_TABLE,
            [
                Service(item="Port 0"),
                Service(item="Port 1"),
                Service(item="Port 8"),
                Service(item="Port 9"),
            ],
        ),
    ],
)
def test_discover_ibm_svc_portfc(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for ibm_svc_portfc check."""
    parsed = parse_ibm_svc_portfc(string_table)
    result = list(discover_ibm_svc_portfc(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "Port 0",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: active, Speed: 8Gb, WWPN: 5005076803042126",
                )
            ],
        ),
        (
            "Port 1",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: active, Speed: 8Gb, WWPN: 5005076803082126",
                )
            ],
        ),
        (
            "Port 8",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: active, Speed: 8Gb, WWPN: 5005076803042127",
                )
            ],
        ),
        (
            "Port 9",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: active, Speed: 8Gb, WWPN: 5005076803082127",
                )
            ],
        ),
    ],
)
def test_check_ibm_svc_portfc(
    item: str, string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    """Test check function for ibm_svc_portfc check."""
    parsed = parse_ibm_svc_portfc(string_table)
    result = list(check_ibm_svc_portfc(item, parsed))
    assert result == expected_results
