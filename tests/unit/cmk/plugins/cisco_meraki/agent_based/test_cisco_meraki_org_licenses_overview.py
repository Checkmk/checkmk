#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from zoneinfo import ZoneInfo

import pytest
import time_machine
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_licenses_overview import (
    check_licenses_overview,
    CheckParams,
    discover_licenses_overview,
    parse_licenses_overview,
)
from cmk.plugins.cisco_meraki.lib.schema import LicensesOverview

_DEFAULT_PARAMS = CheckParams(
    remaining_expiration_time=("no_levels", None),
)


class _LicensesOverviewFactory(TypedDictFactory[LicensesOverview]):
    __check_model__ = False


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_discover_licenses_overview_no_payload(string_table: StringTable) -> None:
    section = parse_licenses_overview(string_table)
    assert not list(discover_licenses_overview(section))


def test_discover_licenses_overview() -> None:
    overviews = [
        _LicensesOverviewFactory.build(organisation_name="Name1", organisation_id="123"),
        _LicensesOverviewFactory.build(organisation_name="Name2", organisation_id="456"),
    ]
    string_table = [[f"{json.dumps(overviews)}"]]
    section = parse_licenses_overview(string_table)

    value = list(discover_licenses_overview(section))
    expected = [Service(item="Name1/123"), Service(item="Name2/456")]

    assert value == expected


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_licenses_overview_no_payload(string_table: StringTable) -> None:
    section = parse_licenses_overview(string_table)
    assert not list(check_licenses_overview("Name1/123", _DEFAULT_PARAMS, section))


@time_machine.travel(datetime.datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC")))
def test_check_licenses_overview() -> None:
    overviews = _LicensesOverviewFactory.build(
        organisation_name="Name1",
        organisation_id="123",
        status="OK",
        expirationDate="Feb 1, 2000 UTC",
        licensedDeviceCounts={"wireless": 1, "MV": 2, "Z1": 3},
    )
    string_table = [[f"[{json.dumps(overviews)}]"]]
    section = parse_licenses_overview(string_table)

    value = list(check_licenses_overview("Name1/123", _DEFAULT_PARAMS, section))
    expected = [
        Result(state=State.OK, notice="Organization ID: 123"),
        Result(state=State.OK, notice="Organization name: Name1"),
        Result(state=State.OK, summary="Status: OK"),
        Result(state=State.OK, summary="Expiration date: 2000-02-01"),
        Result(state=State.OK, summary="Remaining time: 31 days 0 hours"),
        Result(state=State.OK, summary="Number of licensed devices: 6"),
        Result(state=State.OK, notice="MV: 2 licensed devices"),
        Result(state=State.OK, notice="Z1: 3 licensed devices"),
        Result(state=State.OK, notice="wireless: 1 licensed devices"),
    ]

    assert value == expected


def test_check_licenses_overview_bad_status() -> None:
    overview = _LicensesOverviewFactory.build(status="FOO", expirationDate="Feb 1, 2000 UTC")
    string_table = [[f"[{json.dumps(overview)}]"]]
    section = parse_licenses_overview(string_table)
    item = f"{overview['organisation_name']}/{overview['organisation_id']}"
    results = check_licenses_overview(item, _DEFAULT_PARAMS, section)

    value = next(item for item in results if isinstance(item, Result) and item.state == State.WARN)
    expected = Result(state=State.WARN, summary="Status: FOO")

    assert value == expected


@time_machine.travel(datetime.datetime(2000, 2, 2, tzinfo=ZoneInfo("UTC")))
def test_check_licenses_overview_already_expired() -> None:
    overview = _LicensesOverviewFactory.build(status="OK", expirationDate="Feb 1, 2000 UTC")
    string_table = [[f"[{json.dumps(overview)}]"]]
    section = parse_licenses_overview(string_table)
    item = f"{overview['organisation_name']}/{overview['organisation_id']}"
    results = check_licenses_overview(item, _DEFAULT_PARAMS, section)

    value = next(item for item in results if isinstance(item, Result) and item.state == State.CRIT)
    expected = Result(state=State.CRIT, summary="Licenses expired: 1 day 0 hours ago")

    assert value == expected


@time_machine.travel(datetime.datetime(2000, 1, 29, tzinfo=ZoneInfo("UTC")))
def test_check_licenses_overview_remaining_expiration_time_warn() -> None:
    overview = _LicensesOverviewFactory.build(status="OK", expirationDate="Feb 1, 2000 UTC")
    string_table = [[f"[{json.dumps(overview)}]"]]
    section = parse_licenses_overview(string_table)
    item = f"{overview['organisation_name']}/{overview['organisation_id']}"
    params = CheckParams(remaining_expiration_time=("fixed", (3600 * 24 * 4, 3600 * 24 * 2)))
    results = check_licenses_overview(item, params, section)

    value = next(item for item in results if isinstance(item, Result) and item.state == State.WARN)
    expected = Result(
        state=State.WARN,
        summary=("Remaining time: 3 days 0 hours (warn/crit below 4 days 0 hours/2 days 0 hours)"),
    )

    assert value == expected
