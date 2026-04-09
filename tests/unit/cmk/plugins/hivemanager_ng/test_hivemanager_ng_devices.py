#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Service, StringTable
from cmk.legacy_checks.hivemanager_ng_devices import (
    check_hivemanager_ng_devices,
    discover_hivemanager_ng_devices,
    parse_hivemanager_ng_devices,
)

STRING_TABLE_1 = [
    [
        "osVersion::8.1.2.1",
        "ip::10.8.92.100",
        "hostName::Host-1",
        "lastUpdated::2017-11-08T10:01:43.674Z",
        "activeClients::0",
        "connected::True",
        "serialId::00000000000001",
    ],
    [
        "osVersion::8.1.2.1",
        "ip::10.8.92.130",
        "hostName::Host-2",
        "lastUpdated::2017-11-08T10:01:44.056Z",
        "activeClients::14",
        "connected::True",
        "serialId::00000000000002",
    ],
]


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                ("Host-1", {}),
                ("Host-2", {}),
            ],
        ),
    ],
)
def test_discover_hivemanager_ng_devices(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_hivemanager_ng_devices(string_table)
    result = list(discover_hivemanager_ng_devices(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            {
                "Host-1": [
                    (0, "Connected: True"),
                    (0, "active clients: 0", [("connections", 0, 12, 22)]),
                    (0, "IP address: 10.8.92.100"),
                    (0, "serial ID: 00000000000001"),
                    (0, "OS version: 8.1.2.1"),
                    (0, "last updated: 2017-11-08T10:01:43.674Z"),
                ],
                "Host-2": [
                    (0, "Connected: True"),
                    (1, "active clients: 14 (warn/crit at 12/22)", [("connections", 14, 12, 22)]),
                    (0, "IP address: 10.8.92.130"),
                    (0, "serial ID: 00000000000002"),
                    (0, "OS version: 8.1.2.1"),
                    (0, "last updated: 2017-11-08T10:01:44.056Z"),
                ],
            },
        ),
    ],
)
def test_check_hivemanager_ng_devices(
    string_table: StringTable, expected_results: Mapping[str, CheckResult]
) -> None:
    parsed = parse_hivemanager_ng_devices(string_table)
    params = {
        "max_clients": (12, 22),
    }
    result = {
        item_name: list(check_hivemanager_ng_devices(item_name, params, parsed))
        for item_name, _params in discover_hivemanager_ng_devices(parsed)
    }
    assert result == expected_results
