#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Result, Service, State, StringTable, TableRow
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_wireless_ethernet_statuses import (
    check_wireless_ethernet_statuses,
    CheckParams,
    discover_wireless_ethernet_statuses,
    inventory_meraki_wireless_ethernet,
    parse_wireless_ethernet_statuses,
)
from cmk.plugins.cisco_meraki.lib.schema import RawWirelessEthernetStatus


class _RawWirelessEthernetStatusFactory(TypedDictFactory[RawWirelessEthernetStatus]):
    __check_model__ = False


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_discover_wireless_ethernet_statuses_no_payload(string_table: StringTable) -> None:
    section = parse_wireless_ethernet_statuses(string_table)
    assert not list(discover_wireless_ethernet_statuses(section))


def test_discover_wireless_ethernet_statuses() -> None:
    status = _RawWirelessEthernetStatusFactory.build(
        ports=[
            {"name": "port 1", "linkNegotiation": {"speed": "10"}},
            {"name": "port 2", "linkNegotiation": {"speed": None}},
        ]
    )
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    value = list(discover_wireless_ethernet_statuses(section))
    expected = [
        Service(item="port 1", parameters={"speed": 125_000}),
        Service(item="port 2", parameters={"speed": None}),
    ]

    assert value == expected


@pytest.fixture
def params() -> CheckParams:
    return CheckParams(
        state_no_speed=State.WARN.value,
        state_not_full_duplex=State.WARN.value,
        state_not_on_fill_power=State.WARN.value,
        state_speed_change=State.WARN.value,
    )


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_wireless_ethernet_statuses_no_payload(
    string_table: StringTable, params: CheckParams
) -> None:
    section = parse_wireless_ethernet_statuses(string_table)
    assert not list(check_wireless_ethernet_statuses("n/i", params, section))


def test_check_wireless_ethernet_statuses_no_speed_change(params: CheckParams) -> None:
    params["speed"] = 125_000
    status = _RawWirelessEthernetStatusFactory.build(
        ports=[{"name": "port 1", "linkNegotiation": {"speed": "10"}}]
    )
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    value, *_ = list(check_wireless_ethernet_statuses("port 1", params, section))
    expected = Result(state=State.OK, summary="Speed: 1 MBit/s")

    assert value == expected


def test_check_wireless_ethernet_statuses_with_speed_change(params: CheckParams) -> None:
    status = _RawWirelessEthernetStatusFactory.build(
        ports=[{"name": "port 1", "linkNegotiation": {"speed": "10"}}]
    )
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    value = list(check_wireless_ethernet_statuses("port 1", params, section))[:2]
    expected = [
        Result(state=State.WARN, notice="Speed changed: unknown -> 1 MBit/s"),
        Result(state=State.OK, summary="Speed: 1 MBit/s"),
    ]

    assert value == expected


@pytest.mark.parametrize("duplex, state", [("full", 0), ("empty", 1)])
def test_check_wireless_ethernet_statuses_duplex(
    params: CheckParams, duplex: str, state: int
) -> None:
    status = _RawWirelessEthernetStatusFactory.build(
        ports=[{"name": "port 1", "linkNegotiation": {"duplex": duplex}}]
    )
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    value = list(check_wireless_ethernet_statuses("port 1", params, section))[2]
    expected = Result(state=State(state), summary=f"Duplex: {duplex}")

    assert value == expected


@pytest.mark.parametrize("mode, state", [("full", 0), ("empty", 1)])
def test_check_wireless_ethernet_statuses_power_mode(
    params: CheckParams, mode: str, state: int
) -> None:
    status = _RawWirelessEthernetStatusFactory.build(
        power={"mode": mode}, ports=[{"name": "port 1"}]
    )
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    value = list(check_wireless_ethernet_statuses("port 1", params, section))[3]
    expected = Result(state=State(state), notice=f"Power mode: {mode}")

    assert value == expected


@pytest.mark.parametrize("flag, summary", [(True, "connected"), (False, "not connected")])
def test_check_wireless_ethernet_statuses_power(
    params: CheckParams, flag: bool, summary: str
) -> None:
    status = _RawWirelessEthernetStatusFactory.build(
        power={
            "ac": {"isConnected": flag},
            "poe": {"isConnected": flag},
        },
        ports=[{"name": "port 1"}],
    )
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    value = list(check_wireless_ethernet_statuses("port 1", params, section))[4:-1]
    expected = [
        Result(state=State.OK, notice=f"Power AC: {summary}"),
        Result(state=State.OK, notice=f"PoE: {summary}"),
    ]

    assert value == expected


def test_check_wireless_ethernet_statuses_poe_standard(params: CheckParams) -> None:
    status = _RawWirelessEthernetStatusFactory.build(
        ports=[{"name": "port 1", "poe": {"standard": "802.3at"}}],
    )
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    value = list(check_wireless_ethernet_statuses("port 1", params, section))[-1]
    expected = Result(state=State.OK, notice="Standard: 802.3at")

    assert value == expected


def test_inventory_wireless_ethernet_statuses() -> None:
    status = _RawWirelessEthernetStatusFactory.build()
    string_table = [[f"[{json.dumps(status)}]"]]
    section = parse_wireless_ethernet_statuses(string_table)

    row, *_ = list(inventory_meraki_wireless_ethernet(section))

    assert isinstance(row, TableRow)
    assert not row.status_columns
    assert row.path == ["networking", "interfaces"]
    assert set(row.key_columns) == {"index"}
    assert set(row.inventory_columns) == {
        "name",
        "admin_status",
        "oper_status",
        "speed",
        "port_type",
    }


@pytest.mark.parametrize("string_table ", [[], [[]], [[""]]])
def test_inventory_wireless_ethernet_statuses_no_payload(string_table: StringTable) -> None:
    section = parse_wireless_ethernet_statuses(string_table)
    assert not list(inventory_meraki_wireless_ethernet(section))
