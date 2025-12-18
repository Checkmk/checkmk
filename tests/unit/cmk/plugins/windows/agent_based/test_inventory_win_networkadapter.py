#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from ipaddress import (
    IPv4Interface,
    IPv6Interface,
)
from pathlib import Path

import pytest

from cmk.agent_based.v2 import (
    HostLabel,
    HostLabelGenerator,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk.plugins.windows.agent_based.inventory_win_networkadapter import (
    Adapter,
    host_label_win_ip_address,
    inventory_win_ip_address,
    inventory_win_networkadapter,
    parse_win_networkadapter,
    Section,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["AdapterType", " Ethernet 802.3"],
                ["DeviceID", " 7"],
                ["MACAddress", " 08", "00", "27", "9C", "F8", "39"],
                ["Name", " Intel(R) PRO/1000 MT-Desktopadapter 2"],
                ["NetworkAddresses", ""],
                ["ServiceName", " E1G60"],
                ["Speed", " 1000000000"],
                ["Address", " 192.168.178.26"],
                ["Subnet", " 255.255.255.0"],
                ["DefaultGateway", " 192.168.178.1"],
                ["AdapterType", " Ethernet 802.3"],
                ["DeviceID", " 7"],
                ["MACAddress", " 08", "00", "27", "9C", "F8", "39"],
                ["Name", " Intel(R) PRO/1000 MT-Desktopadapter 1"],
                ["NetworkAddresses", ""],
                ["ServiceName", " E1G60"],
                ["Speed", " 1000000000"],
                ["Address", " 192.168.178.26"],
                ["Subnet", " 255.255.255.0"],
                ["DefaultGateway", " 192.168.178.1"],
            ],
            [
                TableRow(
                    path=["hardware", "nwadapter"],
                    key_columns={
                        "name": " Intel(R) PRO/1000 MT-Desktopadapter 1",
                    },
                    inventory_columns={
                        "type": " Ethernet 802.3",
                        "macaddress": " 08:00:27:9C:F8:39",
                        "speed": 1000000000,
                        "gateway": " 192.168.178.1",
                        "ipv4_address": ", 192.168.178.26",
                        "ipv6_address": None,
                        "ipv4_subnet": "255.255.255.0",
                        "ipv6_subnet": None,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "nwadapter"],
                    key_columns={
                        "name": " Intel(R) PRO/1000 MT-Desktopadapter 2",
                    },
                    inventory_columns={
                        "type": " Ethernet 802.3",
                        "macaddress": " 08:00:27:9C:F8:39",
                        "speed": 1000000000,
                        "gateway": " 192.168.178.1",
                        "ipv4_address": ", 192.168.178.26",
                        "ipv6_address": None,
                        "ipv4_subnet": "255.255.255.0",
                        "ipv6_subnet": None,
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_networkadapter(
    string_table: StringTable, expected_result: InventoryResult
) -> None:
    assert (
        list(inventory_win_networkadapter(parse_win_networkadapter(string_table)))
        == expected_result
    )


__section = [
    {
        "type": " Ethernet 802.3",
        "macaddress": " 3C:7C:3F:49:7C:22",
        "name": " ASUS USB-AC68 USB Wireless adapter",
        "speed": 1300000000,
        "ipv4_address": ", 192.168.10.11",
        "ipv6_subnet": "",
        "ipv4_subnet": "255.255.255.0",
    },
    {
        "type": " Ethernet 802.3",
        "name": " VMware Virtual Ethernet Adapter for VMnet1",
        "macaddress": " 00:50:56:C0:00:01",
        "speed": 100000000,
        "ipv4_address": ", 169.254.0.1, 192.168.1.100",
        "ipv4_subnet": "255.255.0.0, 255.255.255.0",
        "ipv6_address": "fe80::5669:a1eb:3add:e9b2, 2c::1",
        "ipv6_subnet": ", 64, 127",
    },
    {
        "type": " Ethernet 802.3",
        "macaddress": " 00:1A:7D:DA:71:06",
        "name": " Bluetooth Device (Personal Area Network)",
    },
    {
        "type": " Ethernet 802.3",
        "macaddress": " 3E:7C:3F:49:7C:22",
        "name": " Microsoft Wi-Fi Direct Virtual Adapter",
        "speed": 9223372036854775807,
    },
    {
        "type": " Ethernet 802.3",
        "macaddress": " 3C:7C:3F:49:7C:22",
        "name": " Microsoft Wi-Fi Direct Virtual Adapter #2",
        "speed": 9223372036854775807,
    },
]


__adapter = Adapter(  # type: ignore[call-arg] # ip_data not known by Adapter
    name="VMware Virtual Ethernet Adapter for VMnet1",
    ipv4_address="169.254.0.1, 192.168.1.100",
    ipv4_subnet="255.255.0.0, 255.255.255.0",
    ipv6_address="fe80::5669:a1eb:3add:e9b2, 2c::1",
    ipv6_subnet="64, 127",
    ip_data=[
        IPv4Interface("169.254.0.1/16"),
        IPv4Interface("192.168.1.100/24"),
        IPv6Interface("fe80::5669:a1eb:3add:e9b2/64"),
        IPv6Interface("2c::1/127"),
    ],
)


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            __section,
            [
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "192.168.10.11",
                        "device": "ASUS USB-AC68 USB Wireless adapter",
                    },
                    inventory_columns={
                        "broadcast": "192.168.10.255",
                        "prefixlength": 24,
                        "netmask": "255.255.255.0",
                        "network": "192.168.10.0",
                        "type": "ipv4",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "169.254.0.1",
                        "device": "VMware Virtual Ethernet Adapter for VMnet1",
                    },
                    inventory_columns={
                        "broadcast": "169.254.255.255",
                        "prefixlength": 16,
                        "netmask": "255.255.0.0",
                        "network": "169.254.0.0",
                        "type": "ipv4",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "192.168.1.100",
                        "device": "VMware Virtual Ethernet Adapter for VMnet1",
                    },
                    inventory_columns={
                        "broadcast": "192.168.1.255",
                        "prefixlength": 24,
                        "netmask": "255.255.255.0",
                        "network": "192.168.1.0",
                        "type": "ipv4",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "fe80::5669:a1eb:3add:e9b2",
                        "device": "VMware Virtual Ethernet Adapter for VMnet1",
                    },
                    inventory_columns={
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                        "prefixlength": 64,
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "network": "fe80::",
                        "type": "ipv6",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_ip_address(section: Section, expected_result: InventoryResult) -> None:
    assert list(inventory_win_ip_address(section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            __section,
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
        ),
    ],
)
def test_host_label_win_ip_address(section: Section, expected_result: HostLabelGenerator) -> None:
    assert list(host_label_win_ip_address(section)) == list(expected_result)


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just set _PYTEST_RAISES=1 and run this file from your IDE and dive into the code.
    source_file_path = (
        (base := (test_file := Path(__file__)).parents[6])
        / test_file.parent.relative_to(base / "tests/unit")
        / test_file.name.lstrip("test_")
    ).as_posix()
    assert pytest.main(["--doctest-modules", source_file_path]) in {0, 5}
    pytest.main(["-vvsx", __file__])
