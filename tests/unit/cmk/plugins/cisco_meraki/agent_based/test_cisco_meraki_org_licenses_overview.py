#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.cisco_meraki.agent_based import cisco_meraki_org_licenses_overview

_STRING_TABLE = [
    [
        (
            '[{"status": "FOO", "expirationDate": "Feb 1, 2000 UTC", "licensedDeviceCounts":'
            '{"wireless": 10, "MV": 20, "Z1": 30, "MS120-48LP": 40, "MS120-48FP": 50, "MX250": 60,'
            '"MX64": 70, "MG21": 80, "MS120-8FP": 90, "MS225-48LP": 100, "MS225-48FP": 110},'
            '"organisation_id": "456", "organisation_name": "Name2"},'
            '{"status": "OK", "expirationDate": "Feb 1, 2000 UTC", "licensedDeviceCounts":'
            '{"wireless": 1, "MV": 2, "Z1": 3, "MS120-48LP": 4, "MS120-48FP": 5, "MX250": 6,'
            '"MX64": 7, "MG21": 8, "MS120-8FP": 9, "MS225-48LP": 10, "MS225-48FP": 11},'
            '"organisation_id": "123", "organisation_name": "Name1"}]'
        ),
    ],
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
                Service(item="Name1/123"),
                Service(item="Name2/456"),
            ],
        ),
    ],
)
def test_discover_licenses_overview(
    string_table: StringTable, expected_services: Sequence[Service]
) -> None:
    section = cisco_meraki_org_licenses_overview.parse_licenses_overview(string_table)
    assert sorted(expected_services) == sorted(
        cisco_meraki_org_licenses_overview.discover_licenses_overview(section)
    )


@pytest.mark.parametrize(
    "string_table, item, expected_results",
    [
        # without params
        ([], "Name1/123", []),
        ([], "Name2/456", []),
        ([], "Name3/789", []),
        ([[]], "Name1/123", []),
        ([[]], "Name2/456", []),
        ([[]], "Name3/789", []),
        ([[""]], "Name1/123", []),
        ([[""]], "Name2/456", []),
        ([[""]], "Name3/789", []),
        (
            _STRING_TABLE,
            "Name1/123",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Expiration date: Feb 01, 2000"),
                Result(state=State.OK, summary="Remaining time: 31 days 0 hours"),
                Result(state=State.OK, summary="Number of licensed devices: 66"),
                Result(state=State.OK, notice="MG21: 8 licensed devices"),
                Result(state=State.OK, notice="MS120-48FP: 5 licensed devices"),
                Result(state=State.OK, notice="MS120-48LP: 4 licensed devices"),
                Result(state=State.OK, notice="MS120-8FP: 9 licensed devices"),
                Result(state=State.OK, notice="MS225-48FP: 11 licensed devices"),
                Result(state=State.OK, notice="MS225-48LP: 10 licensed devices"),
                Result(state=State.OK, notice="MV: 2 licensed devices"),
                Result(state=State.OK, notice="MX250: 6 licensed devices"),
                Result(state=State.OK, notice="MX64: 7 licensed devices"),
                Result(state=State.OK, notice="Z1: 3 licensed devices"),
                Result(state=State.OK, notice="wireless: 1 licensed devices"),
            ],
        ),
        (
            _STRING_TABLE,
            "Name2/456",
            [
                Result(state=State.WARN, summary="Status: FOO"),
                Result(state=State.OK, summary="Expiration date: Feb 01, 2000"),
                Result(state=State.OK, summary="Remaining time: 31 days 0 hours"),
                Result(state=State.OK, summary="Number of licensed devices: 660"),
                Result(state=State.OK, notice="MG21: 80 licensed devices"),
                Result(state=State.OK, notice="MS120-48FP: 50 licensed devices"),
                Result(state=State.OK, notice="MS120-48LP: 40 licensed devices"),
                Result(state=State.OK, notice="MS120-8FP: 90 licensed devices"),
                Result(state=State.OK, notice="MS225-48FP: 110 licensed devices"),
                Result(state=State.OK, notice="MS225-48LP: 100 licensed devices"),
                Result(state=State.OK, notice="MV: 20 licensed devices"),
                Result(state=State.OK, notice="MX250: 60 licensed devices"),
                Result(state=State.OK, notice="MX64: 70 licensed devices"),
                Result(state=State.OK, notice="Z1: 30 licensed devices"),
                Result(state=State.OK, notice="wireless: 10 licensed devices"),
            ],
        ),
        (_STRING_TABLE, "Name3/789", []),
    ],
)
def test_check_licenses_overview(
    string_table: StringTable, item: str, expected_results: Sequence[Result]
) -> None:
    section = cisco_meraki_org_licenses_overview.parse_licenses_overview(string_table)
    with time_machine.travel(datetime.datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC"))):
        assert (
            list(cisco_meraki_org_licenses_overview.check_licenses_overview(item, {}, section))
            == expected_results
        )


@pytest.mark.parametrize(
    "string_table, item, expected_results",
    [
        (
            _STRING_TABLE,
            "Name1/123",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Expiration date: Feb 01, 2000"),
                Result(state=State.CRIT, summary="Licenses expired: 1 day 0 hours ago"),
                Result(state=State.OK, summary="Number of licensed devices: 66"),
                Result(state=State.OK, notice="MG21: 8 licensed devices"),
                Result(state=State.OK, notice="MS120-48FP: 5 licensed devices"),
                Result(state=State.OK, notice="MS120-48LP: 4 licensed devices"),
                Result(state=State.OK, notice="MS120-8FP: 9 licensed devices"),
                Result(state=State.OK, notice="MS225-48FP: 11 licensed devices"),
                Result(state=State.OK, notice="MS225-48LP: 10 licensed devices"),
                Result(state=State.OK, notice="MV: 2 licensed devices"),
                Result(state=State.OK, notice="MX250: 6 licensed devices"),
                Result(state=State.OK, notice="MX64: 7 licensed devices"),
                Result(state=State.OK, notice="Z1: 3 licensed devices"),
                Result(state=State.OK, notice="wireless: 1 licensed devices"),
            ],
        ),
    ],
)
def test_check_licenses_overview_already_expired(
    string_table: StringTable, item: str, expected_results: Sequence[Result]
) -> None:
    section = cisco_meraki_org_licenses_overview.parse_licenses_overview(string_table)
    with time_machine.travel(datetime.datetime(2000, 2, 2, tzinfo=ZoneInfo("UTC"))):
        assert (
            list(cisco_meraki_org_licenses_overview.check_licenses_overview(item, {}, section))
            == expected_results
        )


@pytest.mark.parametrize(
    "string_table, item, params, expected_results",
    [
        (
            _STRING_TABLE,
            "Name1/123",
            {"remaining_expiration_time": (3600 * 24 * 4, 3600 * 24 * 2)},
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Expiration date: Feb 01, 2000"),
                Result(
                    state=State.WARN,
                    summary=(
                        "Remaining time: 3 days 0 hours"
                        " (warn/crit below 4 days 0 hours/2 days 0 hours)"
                    ),
                ),
                Result(state=State.OK, summary="Number of licensed devices: 66"),
                Result(state=State.OK, notice="MG21: 8 licensed devices"),
                Result(state=State.OK, notice="MS120-48FP: 5 licensed devices"),
                Result(state=State.OK, notice="MS120-48LP: 4 licensed devices"),
                Result(state=State.OK, notice="MS120-8FP: 9 licensed devices"),
                Result(state=State.OK, notice="MS225-48FP: 11 licensed devices"),
                Result(state=State.OK, notice="MS225-48LP: 10 licensed devices"),
                Result(state=State.OK, notice="MV: 2 licensed devices"),
                Result(state=State.OK, notice="MX250: 6 licensed devices"),
                Result(state=State.OK, notice="MX64: 7 licensed devices"),
                Result(state=State.OK, notice="Z1: 3 licensed devices"),
                Result(state=State.OK, notice="wireless: 1 licensed devices"),
            ],
        ),
        (
            _STRING_TABLE,
            "Name1/123",
            {"remaining_expiration_time": (3600 * 24 * 5, 3600 * 24 * 4)},
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Expiration date: Feb 01, 2000"),
                Result(
                    state=State.CRIT,
                    summary=(
                        "Remaining time: 3 days 0 hours"
                        " (warn/crit below 5 days 0 hours/4 days 0 hours)"
                    ),
                ),
                Result(state=State.OK, summary="Number of licensed devices: 66"),
                Result(state=State.OK, notice="MG21: 8 licensed devices"),
                Result(state=State.OK, notice="MS120-48FP: 5 licensed devices"),
                Result(state=State.OK, notice="MS120-48LP: 4 licensed devices"),
                Result(state=State.OK, notice="MS120-8FP: 9 licensed devices"),
                Result(state=State.OK, notice="MS225-48FP: 11 licensed devices"),
                Result(state=State.OK, notice="MS225-48LP: 10 licensed devices"),
                Result(state=State.OK, notice="MV: 2 licensed devices"),
                Result(state=State.OK, notice="MX250: 6 licensed devices"),
                Result(state=State.OK, notice="MX64: 7 licensed devices"),
                Result(state=State.OK, notice="Z1: 3 licensed devices"),
                Result(state=State.OK, notice="wireless: 1 licensed devices"),
            ],
        ),
    ],
)
def test_check_licenses_overview_remaining_expiration_time(
    string_table: StringTable, item: str, params: Mapping, expected_results: Sequence[Result]
) -> None:
    section = cisco_meraki_org_licenses_overview.parse_licenses_overview(string_table)
    with time_machine.travel(datetime.datetime(2000, 1, 29, tzinfo=ZoneInfo("UTC"))):
        assert (
            list(cisco_meraki_org_licenses_overview.check_licenses_overview(item, params, section))
            == expected_results
        )
