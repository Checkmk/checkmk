#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based import if64
from cmk.plugins.lib import if64 as if64_lib
from cmk.plugins.lib import interfaces


def test_parse_if64adm() -> None:
    assert if64.parse_if64adm(
        [
            ["1", "1"],
            ["2", ""],
            ["3", "2"],
        ]
    ) == {
        "1": "1",
        "3": "2",
    }


def test_parse_if_name() -> None:
    # Rows are [ifIndex, ifName]. Empty names and non-positive ifIndex values are dropped.
    assert if64.parse_if_name(
        [
            ["1", "lo"],
            ["2", "port1.5"],
            ["3", ""],
            ["0", "invalid index"],
        ]
    ) == {
        "1": "lo",
        "2": "port1.5",
    }


def test_parse_if_name_keys_by_ifindex_not_table_row() -> None:
    # Non-compliant agent (e.g. Ubiquiti Wave AP, SUP-27628): the ifTable/ifXTable are indexed
    # by a plain row number 1..5, while the ifIndex column reports 5, 8, 9, 3, 4. Fetching the
    # ifIndex column (not OIDEnd) pairs each ifName with its real ifIndex, so the section is
    # keyed by the ifIndex value and later joins onto the right interface.
    assert if64.parse_if_name(
        [
            ["5", "wlan0"],
            ["8", "ath0"],
            ["9", "br0"],
            ["3", "eth0"],
            ["4", "eth1"],
        ]
    ) == {
        "5": "wlan0",
        "8": "ath0",
        "9": "br0",
        "3": "eth0",
        "4": "eth1",
    }


def test_parse_if_name_switch_with_large_indices() -> None:
    assert if64.parse_if_name(
        [
            ["1", "1/1/1"],
            ["52", "1/1/52"],
            ["769", "lag1"],
            ["16777217", "vlan1"],
            ["268435456", "eth0"],
        ]
    ) == {
        "1": "1/1/1",
        "52": "1/1/52",
        "769": "lag1",
        "16777217": "vlan1",
        "268435456": "eth0",
    }


def test_add_names_to_ifaces_row_index_differs_from_ifindex() -> None:
    # The name of the interface with ifIndex 3 must be "eth0", not the name that happens to
    # sit at table row 3. Getting this wrong cross-assigns names and, during discovery,
    # inflates the duplicate-item counter so unique aliases gain a spurious index suffix.
    ifaces = [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(index=index, descr=descr, alias=descr, type="6"),
            interfaces.Counters(),
            123.0,
        )
        for index, descr in (("5", "wlan0"), ("8", "ath0"), ("3", "eth0"), ("4", "eth1"))
    ]
    if64_lib.add_names_to_ifaces(
        ifaces,
        {"5": "wlan0", "8": "ath0", "9": "br0", "3": "eth0", "4": "eth1"},
    )
    assert [iface.attributes.name for iface in ifaces] == ["wlan0", "ath0", "eth0", "eth1"]


def test_add_admin_status_to_ifaces() -> None:
    ifaces = [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="1",
                descr="GigabitEthernet1/1",
                alias="** Trunk to main switch **",
                type="6",
            ),
            interfaces.Counters(),
            123.0,
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="2",
                descr="Primary Internet connection",
                alias="",
                type="6",
            ),
            interfaces.Counters(),
            123.0,
        ),
    ]
    if64._add_admin_status_to_ifaces(ifaces, {"1": "1"})
    assert ifaces[0].attributes.admin_status == "1"
    assert ifaces[1].attributes.admin_status is None


def test_check_timestamps_decrease() -> None:
    value_store: dict[str, object] = {}
    assert not list(if64._check_timestamps({"a": 1, "b": 2}, value_store))
    assert list(if64._check_timestamps({"a": 0, "b": 1}, value_store)) == [
        Result(
            state=State.OK,
            notice="The uptime has decreased since the last check cycle for these node(s): \nThe device might have rebooted or its uptime counter overflowed.",
        )
    ]


def test_check_timestamps_no_change() -> None:
    value_store: dict[str, object] = {}
    assert not list(if64._check_timestamps({"a": 1, "b": 2}, value_store))
    assert list(if64._check_timestamps({"a": 1, "b": 2}, value_store)) == [
        Result(
            state=State.OK,
            notice="The uptime did not change since the last check cycle for these node(s): a, b\nIt is likely that no new data was collected.",
        )
    ]


def test_check_timestamps_valid() -> None:
    value_store: dict[str, object] = {}
    assert not list(if64._check_timestamps({"a": 1, "b": 2}, value_store))
    assert not list(if64._check_timestamps({"a": 61, "b": 62}, value_store))


def test_parse_snmp_uptime_pair_with_empty_section_is_none() -> None:
    parsed_uptime = if64.parse_snmp_uptime_pair([[]])
    assert parsed_uptime is None


def test_parse_snmp_uptime_pair_with_no_values_is_not_valid() -> None:
    parsed_uptime = if64.parse_snmp_uptime_pair([["", ""]])

    assert parsed_uptime is not None
    assert not parsed_uptime
    assert len(parsed_uptime.to_list()) == 0
    assert parsed_uptime.sys_uptime_sec is None
    assert parsed_uptime.hr_sys_uptime_sec is None


def test_parse_snmp_uptime_pair_with_sys_uptime_only_has_parsed_value() -> None:
    parsed_uptime = if64.parse_snmp_uptime_pair([["500000", ""]])

    assert parsed_uptime
    assert len(parsed_uptime.to_list()) == 1
    assert parsed_uptime.sys_uptime_sec == 5000
    assert parsed_uptime.hr_sys_uptime_sec is None


def test_parse_snmp_uptime_pair_with_hr_sys_uptime_only_has_parsed_value() -> None:
    parsed_uptime = if64.parse_snmp_uptime_pair([["", "500000"]])

    assert parsed_uptime
    assert len(parsed_uptime.to_list()) == 1
    assert parsed_uptime.sys_uptime_sec is None
    assert parsed_uptime.hr_sys_uptime_sec == 5000


def test_parse_snmp_uptime_pair_with_both_uptime_values_has_parsed_values() -> None:
    parsed_uptime = if64.parse_snmp_uptime_pair([["500000", "500500"]])

    assert parsed_uptime
    assert len(parsed_uptime.to_list()) == 2
    assert parsed_uptime.sys_uptime_sec == 5000
    assert parsed_uptime.hr_sys_uptime_sec == 5005


def test_parse_snmp_uptime_pair_with_both_values_but_hr_uptime_is_zero_second_value_is_not_none() -> (
    None
):
    parsed_uptime = if64.parse_snmp_uptime_pair([["500000", "0"]])

    assert parsed_uptime
    assert len(parsed_uptime.to_list()) == 2
    assert parsed_uptime.sys_uptime_sec == 5000
    assert parsed_uptime.hr_sys_uptime_sec == 0
