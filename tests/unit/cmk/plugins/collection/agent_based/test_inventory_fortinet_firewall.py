#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import StringTable, TableRow
from cmk.plugins.collection.agent_based.inventory_fortinet_firewall import (
    Interface,
    inventory_fortinet_firewall,
    parse_fortinet_firewall_network_interfaces,
    SectionFortinetInterface,
)


def test_parse_inventory_fortinet_firewall() -> None:
    string_table = [
        [
            ["127.0.0.1", "20", "255.255.255.0"],
            ["127.0.0.2", "21", "255.255.255.224"],
            ["127.0.0.3", "22", "255.255.255.224"],
            ["127.0.0.4", "25", "255.255.255.224"],
            ["127.0.0.5", "133", "255.255.255.224"],
        ],
        [
            ["20", "internal1.101"],
            ["21", "internal1.102"],
            ["22", "internal1.103"],
            ["25", "internal1.106"],
            ["133", "internal1.107"],
        ],
    ]

    expected_parse_result = {
        "127.0.0.1": Interface(
            if_index="20",
            if_name="internal1.101",
            ip_address="127.0.0.1",
            address_type="IPv4",
            subnet=["255.255.255.0"],
        ),
        "127.0.0.2": Interface(
            if_index="21",
            if_name="internal1.102",
            ip_address="127.0.0.2",
            address_type="IPv4",
            subnet=["255.255.255.224"],
        ),
        "127.0.0.3": Interface(
            if_index="22",
            if_name="internal1.103",
            ip_address="127.0.0.3",
            address_type="IPv4",
            subnet=["255.255.255.224"],
        ),
        "127.0.0.4": Interface(
            if_index="25",
            if_name="internal1.106",
            ip_address="127.0.0.4",
            address_type="IPv4",
            subnet=["255.255.255.224"],
        ),
        "127.0.0.5": Interface(
            if_index="133",
            if_name="internal1.107",
            ip_address="127.0.0.5",
            address_type="IPv4",
            subnet=["255.255.255.224"],
        ),
    }

    parse_result = parse_fortinet_firewall_network_interfaces(string_table)

    assert parse_result == expected_parse_result


def test_parse_inventory_fortinet_firewall_empty_string_table() -> None:
    string_table: list[StringTable] = []

    expected_parse_result: SectionFortinetInterface = {}

    parse_result = parse_fortinet_firewall_network_interfaces(string_table)

    assert parse_result == expected_parse_result


def test_inventory_fortinet_firewall_with_section() -> None:
    section = {
        "127.0.0.3": Interface(
            if_index="22",
            if_name="internal1.103",
            ip_address="127.0.0.3",
            address_type="IPv4",
            subnet=["255.255.255.224"],
        ),
    }

    inventory_result = inventory_fortinet_firewall(section)

    expected_inventory_result = [
        TableRow(
            path=["networking", "addresses"],
            key_columns={
                "address": "127.0.0.3",
            },
            inventory_columns={
                "index": "22",
                "device": "internal1.103",
                "type": "IPv4",
                "subnet": "255.255.255.224",
            },
        )
    ]

    assert list(inventory_result) == expected_inventory_result


def test_inventory_fortinet_firewall_no_section() -> None:
    section: SectionFortinetInterface = {}

    inventory_result = inventory_fortinet_firewall(section)

    expected_inventory_result: Sequence[TableRow] = []

    assert list(inventory_result) == expected_inventory_result
