#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.cisco_asa_conn import (
    check_cisco_asa_conn,
    inventory_cisco_asa_conn,
    NetworkInterfaceData,
    parse_cisco_asa_conn,
    Section,
)

string_table: Sequence[StringTable] = [
    [
        ["2", "GigabitEthernet1/1"],
        ["14", "management"],
        ["29", "INSIDE-115"],
    ],
    [
        ["14", "172.21.212.23"],
        ["29", "172.21.212.243"],
        ["38", "172.21.213.99"],
    ],
    [["2", "1", "1"], ["14", "1", "1"], ["29", "1", "1"]],
]

parsed_section: Section = {
    "2": NetworkInterfaceData(if_name="GigabitEthernet1/1", admin_status="1", oper_status="1"),
    "14": NetworkInterfaceData(
        if_name="management", admin_status="1", oper_status="1", ip_address="172.21.212.23"
    ),
    "38": NetworkInterfaceData(ip_address="172.21.213.99", admin_status="1"),
    "29": NetworkInterfaceData(
        if_name="INSIDE-115", admin_status="1", oper_status="1", ip_address="172.21.212.243"
    ),
}


def test_parse_cisco_asa_conn() -> None:
    assert parsed_section == parse_cisco_asa_conn(string_table)


def test_inventory_cisco_asa_conn() -> None:
    inventory: Sequence[Service] = list(inventory_cisco_asa_conn(parsed_section))

    assert len(inventory) == 3
    assert inventory[0].item == "14"


def _get_ip_result(results: Sequence) -> Result:
    return [r for r in results if isinstance(r, Result) and r.summary.startswith("IP:")][0]


def test_check_cisco_asa_conn_undefined_network_interface() -> None:
    results: Sequence = list(check_cisco_asa_conn("38", parsed_section))
    ip_result: Result = _get_ip_result(results)
    assert "No network device associated" in ip_result.summary
    assert ip_result.state == State.UNKNOWN


def test_check_cisco_asa_conn_undefined_ip_address() -> None:
    results: Sequence = list(check_cisco_asa_conn("2", parsed_section))
    ip_result: Result = _get_ip_result(results)
    assert "Not found" in ip_result.summary
    assert ip_result.state == State.CRIT


def test_check_cisco_asa_conn_default() -> None:
    results: Sequence = list(check_cisco_asa_conn("14", parsed_section))
    expected_summaries: set[str] = {"Name: management", "IP: 172.21.212.23", "Status: up"}
    actual_summaries = {res.summary for res in results if isinstance(res, Result)}
    assert actual_summaries == expected_summaries
    assert all(res.state == State.OK for res in results if isinstance(res, Result))
