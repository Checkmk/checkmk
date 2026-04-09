#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, StringTable
from cmk.legacy_checks.hivemanager_devices import (
    check_hivemanager_devices,
    discover_hivemanager_devices,
    parse_hivemanager_devices,
)

STRING_TABLE_1 = [
    [
        "upTime::5 Days, 22 Hrs 20 Mins 30 Secs",
        "networkPolicy::Hotspot-C4W",
        "hostName::Hostname1",
        "nodeId::DEADBEEF0001",
        "location::12.34567, 4.567897",
        "eth0LLDPSysName::-",
        "hiveOS::HiveOS 6.1r3b.2026",
        "hive::PublicWiFi1",
        "alarm::Cleared",
        "clients::10",
        "connection::True",
        "eth0LLDPPort::-",
    ],
    [
        "upTime::9 Days, 18 Hrs 28 Mins 18 Secs",
        "networkPolicy::Hotspot-C4W",
        "hostName::Hostname2",
        "nodeId::DEADBEEF0002",
        "location::12.34567, 5.678901",
        "eth0LLDPSysName::-",
        "hiveOS::HiveOS 6.1r2b.2026",
        "hive::PublicWiFi2",
        "alarm::Maybe",
        "clients::20",
        "connection::False",
        "eth0LLDPPort::-",
    ],
    [
        "upTime::12 Days, 18 Hrs 28 Mins 18 Secs",
        "networkPolicy::Hotspot-C4W",
        "hostName::Hostname3",
        "nodeId::DEADBEEF0002",
        "location::12.34567, 5.678901",
        "eth0LLDPSysName::-",
        "hiveOS::HiveOS 6.1r2b.2026",
        "hive::PublicWiFi2",
        "alarm::Critical",
        "clients::30",
        "connection::True",
        "eth0LLDPPort::-",
    ],
]


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                ("Hostname1", {}),
                ("Hostname2", {}),
                ("Hostname3", {}),
            ],
        ),
    ],
)
def test_discover_hivemanager_devices(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, object]]]
) -> None:
    parsed = parse_hivemanager_devices(string_table)
    result = list(discover_hivemanager_devices(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            {
                "Hostname1": [
                    (
                        0,
                        "Clients: 10",
                        [("client_count", 10, 12, 22)],
                    ),
                    (
                        0,
                        "Uptime: 5 days 22 hours",
                        [("uptime", 512430, 691208, 864010)],
                    ),
                    (
                        0,
                        "networkPolicy: Hotspot-C4W, nodeId: DEADBEEF0001, location: "
                        "12.34567, 4.567897, hiveOS: HiveOS 6.1r3b.2026, hive: "
                        "PublicWiFi1",
                    ),
                ],
                "Hostname2": [
                    (
                        0,
                        "networkPolicy: Hotspot-C4W, nodeId: DEADBEEF0002, location: "
                        "12.34567, 5.678901, hiveOS: HiveOS 6.1r2b.2026, hive: "
                        "PublicWiFi2",
                    ),
                    (
                        1,
                        "Alarm state: Maybe",
                    ),
                    (
                        1,
                        "Clients: 20 Warn/Crit at 12/22",
                        [("client_count", 20, 12, 22)],
                    ),
                    (
                        1,
                        "Uptime: 9 days 18 hours (warn/crit at 8 days 0 hours/10 days 0 hours)",
                        [("uptime", 844098, 691208, 864010)],
                    ),
                    (
                        2,
                        "Connection lost",
                    ),
                ],
                "Hostname3": [
                    (
                        0,
                        "networkPolicy: Hotspot-C4W, nodeId: DEADBEEF0002, location: "
                        "12.34567, 5.678901, hiveOS: HiveOS 6.1r2b.2026, hive: "
                        "PublicWiFi2",
                    ),
                    (
                        2,
                        "Alarm state: Critical",
                    ),
                    (
                        2,
                        "Clients: 30 Warn/Crit at 12/22",
                        [("client_count", 30, 12, 22)],
                    ),
                    (
                        2,
                        "Uptime: 12 days 18 hours (warn/crit at 8 days 0 hours/10 days 0 hours)",
                        [("uptime", 1103298, 691208, 864010)],
                    ),
                ],
            },
        ),
    ],
)
def test_check_hivemanager_devices(
    string_table: StringTable, expected_results: Mapping[str, CheckResult]
) -> None:
    parsed = parse_hivemanager_devices(string_table)
    params = {
        "alert_on_loss": True,
        "max_clients": (12, 22),
        "crit_states": ["Critical"],
        "warn_states": ["Maybe", "Major", "Minor"],
        "max_uptime": (86401 * 8, 86401 * 10),
    }
    result = {
        item_name: sorted(check_hivemanager_devices(item_name, params, parsed))
        for item_name, _params in discover_hivemanager_devices(parsed)
    }
    assert result == expected_results
