#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.meraki.agent_based import cisco_meraki_org_device_status

_STRING_TABLE = [
    [
        (
            '[{"name": "My AP", "serial": "Q234-ABCD-5678", "mac": "00:11:22:33:44:55",'
            '"publicIp": "123.123.123.1", "networkId": "N_24329156", "status": "online",'
            '"lastReportedAt": "2000-01-14T00:00:00.090210Z", "lanIp": "1.2.3.4",'
            '"gateway": "1.2.3.5", "ipType": "dhcp", "primaryDns": "8.8.8.8",'
            '"secondaryDns": "8.8.4.4", "productType": "wireless",'
            '"components": {"powerSupplies": []}, "model": "MR34",'
            '"tags": ["tag1", "tag2"]}]'
        ),
    ]
]


_STRING_TABLE_OFFLINE = [
    [
        (
            '[{"name": "My AP", "serial": "Q234-ABCD-5678", "mac": "00:11:22:33:44:55",'
            '"publicIp": "123.123.123.1", "networkId": "N_24329156", "status": "offline",'
            '"lastReportedAt": "2000-01-14T00:00:00.090210Z", "lanIp": "1.2.3.4",'
            '"gateway": "1.2.3.5", "ipType": "dhcp", "primaryDns": "8.8.8.8",'
            '"secondaryDns": "8.8.4.4", "productType": "wireless",'
            '"components": {"powerSupplies": []}, "model": "MR34",'
            '"tags": ["tag1", "tag2"]}]'
        ),
    ]
]


@pytest.mark.parametrize(
    "string_table, expected_services",
    [
        ([], []),
        ([[]], []),
        ([[""]], []),
        (
            _STRING_TABLE,
            [
                Service(),
            ],
        ),
        (
            _STRING_TABLE_OFFLINE,
            [Service()],
        ),
    ],
)
def test_discover_device_status(
    string_table: StringTable, expected_services: Sequence[Service]
) -> None:
    section = cisco_meraki_org_device_status.parse_device_status(string_table)
    assert sorted(expected_services) == sorted(
        cisco_meraki_org_device_status.discover_device_status(section)
    )


@pytest.mark.parametrize(
    "string_table, expected_results",
    [
        ([], []),
        ([[]], []),
        ([[""]], []),
        (
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.OK, summary="Time since last report: 23 hours 59 minutes"),
                Metric("last_reported", 86399.90979003906),
            ],
        ),
    ],
)
def test_check_device_status(string_table: StringTable, expected_results: Sequence[Result]) -> None:
    section = cisco_meraki_org_device_status.parse_device_status(string_table)
    with time_machine.travel(datetime.datetime(2000, 1, 15, tzinfo=ZoneInfo("UTC"))):
        assert (
            list(
                cisco_meraki_org_device_status.check_device_status(
                    cisco_meraki_org_device_status.Parameters(),
                    section,
                )
            )
            == expected_results
        )
