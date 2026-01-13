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

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable, TableRow
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_device_status import (
    check_device_status,
    check_device_status_ps,
    DeviceStatus,
    discover_device_status,
    discover_device_status_ps,
    inventory_power_supplies,
    Parameters,
    parse_device_status,
)
from cmk.plugins.cisco_meraki.lib.schema._devices_statuses import RawDevicesStatus


class _RawDevicesStatusFactory(TypedDictFactory[RawDevicesStatus]):
    __check_model__ = False

    @classmethod
    def lastReportedAt(cls) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d")


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_parse_device_status_no_payload(string_table: StringTable) -> None:
    assert not parse_device_status(string_table)


@pytest.mark.parametrize(
    "device_status",
    [
        _RawDevicesStatusFactory.build(status="powering"),
        _RawDevicesStatusFactory.build(status="offline"),
    ],
)
def test_discover_device_status(device_status: RawDevicesStatus) -> None:
    string_table = _get_string_table_from_device_status(device_status)
    section = _parse_and_assert_not_none(string_table)

    value = sorted(discover_device_status(section))
    expected = [Service()]

    assert value == expected


@time_machine.travel(datetime.datetime(2000, 1, 15, tzinfo=ZoneInfo("UTC")))
def test_check_device_status() -> None:
    device_status = _RawDevicesStatusFactory.build(status="online", lastReportedAt="2000-01-14")
    string_table = _get_string_table_from_device_status(device_status)
    section = _parse_and_assert_not_none(string_table)
    params = Parameters()

    value = list(check_device_status(params, section=section))
    expected = [
        Result(state=State.OK, summary="Status: online"),
        Result(state=State.OK, summary="Time since last report: 1 day 0 hours"),
        Metric("last_reported", 86400.0),
    ]

    assert value == expected


@pytest.mark.parametrize(
    ("device_status", "expected"),
    [
        (_RawDevicesStatusFactory.build(), 1),
        (_RawDevicesStatusFactory.build(components={"powerSupplies": []}), 0),
    ],
)
def test_discover_device_status_ps(device_status: RawDevicesStatus, expected: int) -> None:
    string_table = _get_string_table_from_device_status(device_status)
    section = _parse_and_assert_not_none(string_table)
    value = list(discover_device_status_ps(section))
    assert len(value) == expected


def test_check_device_status_ps() -> None:
    device_status = _RawDevicesStatusFactory.build()
    device_status["components"]["powerSupplies"][0].update(
        {
            "slot": 1,
            "status": "powering",
            "model": "PWR-MS320-1025WAC",
            "serial": "QABC-1234-5678",
        }
    )
    string_table = _get_string_table_from_device_status(device_status)
    section = _parse_and_assert_not_none(string_table)

    value = list(check_device_status_ps("1", {}, section))
    expected = [
        Result(state=State.OK, summary="Status: powering"),
        Result(state=State.OK, notice="Model: PWR-MS320-1025WAC"),
        Result(state=State.OK, notice="Serial: QABC-1234-5678"),
    ]

    assert value == expected


def test_check_device_status_ps_not_powering() -> None:
    device_status = _RawDevicesStatusFactory.build()
    device_status["components"]["powerSupplies"][0].update({"slot": 1, "status": "off"})
    string_table = _get_string_table_from_device_status(device_status)
    section = _parse_and_assert_not_none(string_table)

    value = list(check_device_status_ps("1", {}, section))[0]
    expected = Result(state=State.WARN, summary="Status: off")

    assert value == expected


def test_inventory_power_supplies() -> None:
    device_status = _RawDevicesStatusFactory.build(
        components={
            "powerSupplies": [
                {
                    "slot": 1,
                    "serial": "QABC-1234-5678",
                    "model": "PWR-MS320-1025WAC",
                    "status": "powering",
                    "poe": {"unit": "watts", "maximum": 740},
                },
            ]
        },
    )
    string_table = _get_string_table_from_device_status(device_status)
    section = _parse_and_assert_not_none(string_table)

    value = list(inventory_power_supplies(section))
    expected = [
        TableRow(
            path=["hardware", "components", "psus"],
            key_columns={
                "index": 1,
                "serial": "QABC-1234-5678",
            },
            inventory_columns={
                "model": "PWR-MS320-1025WAC",
                "location": "Slot 1",
                "manufacturer": "Cisco Meraki",
            },
            status_columns={},
        )
    ]

    assert value == expected


def _get_string_table_from_device_status(device_status: RawDevicesStatus) -> StringTable:
    return [[f"[{json.dumps(device_status)}]"]]


def _parse_and_assert_not_none(
    string_table: StringTable,
) -> DeviceStatus:
    section = parse_device_status(string_table)
    assert section
    return section
