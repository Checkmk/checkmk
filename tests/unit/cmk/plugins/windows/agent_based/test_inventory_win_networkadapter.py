#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

import pytest

from cmk.agent_based.v2 import (
    HostLabel,
    HostLabelGenerator,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk.plugins.lib.interfaces import (
    AugmentedIPv4Interface,
    AugmentedIPv6Interface,
    IPNetworkAdapter,
)
from cmk.plugins.windows.agent_based.inventory_win_networkadapter import (
    host_label_win_ip_address,
    inventorize_ip_addresses_windows,
    inventory_win_networkadapter,
    parse_win_networkadapter,
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
                    key_columns={"name": "Intel(R) PRO/1000 MT-Desktopadapter 1"},
                    inventory_columns={
                        "type": "Ethernet 802.3",
                        "macaddress": "08:00:27:9C:F8:39",
                        "speed": 1000000000,
                        "gateway": "192.168.178.1",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "nwadapter"],
                    key_columns={"name": "Intel(R) PRO/1000 MT-Desktopadapter 2"},
                    inventory_columns={
                        "type": "Ethernet 802.3",
                        "macaddress": "08:00:27:9C:F8:39",
                        "speed": 1000000000,
                        "gateway": "192.168.178.1",
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
    ["AdapterType", " Ethernet 802.3"],
    ["MACAddress", " AA", "BB", "CC", "DD", "7C", "22"],
    ["Name", " ASUS USB-AC68 USB Wireless adapter"],
    ["Speed", " 1300000000"],
    ["Address", " 192.168.10.11"],
    ["Subnet", " 255.255.255.0"],
    ["AdapterType", " Ethernet 802.3"],
    ["Name", " VMware Virtual Ethernet Adapter for VMnet1"],
    ["MACAddress", " AA", "BB", "CC", "DD", "00", "01"],
    ["Speed", " 100000000"],
    ["Address", " 169.254.0.1 192.168.1.100 fe80::5669:a1eb:3add:e9b2 2c::1"],
    ["Subnet", " 255.255.0.0 255.255.255.0 64 127"],
    ["AdapterType", " Ethernet 802.3"],
    ["MACAddress", " AA", "BB", "CC", "DD", "71", "06"],
    ["Name", " Bluetooth Device (Personal Area Network)"],
    ["AdapterType", " Ethernet 802.3"],
    ["MACAddress", " AA", "BB", "CC", "DD", "7C", "22"],
    ["Name", " Microsoft Wi-Fi Direct Virtual Adapter"],
    ["Speed", " 9223372036854775807"],
    ["AdapterType", " Ethernet 802.3"],
    ["MACAddress", " AA", "BB", "CC", "DD", "7C", "22"],
    ["Name", " Microsoft Wi-Fi Direct Virtual Adapter #2"],
    ["Speed", " 9223372036854775807"],
]


__adapter = IPNetworkAdapter(
    name="VMware Virtual Ethernet Adapter for VMnet1",
    inet4=[
        AugmentedIPv4Interface("169.254.0.1/255.255.0.0"),
        AugmentedIPv4Interface("192.168.1.100/255.255.255.0"),
    ],
    inet6=[
        AugmentedIPv6Interface("fe80::5669:a1eb:3add:e9b2/64"),
        AugmentedIPv6Interface("2c::1/127"),
    ],
)


@pytest.mark.parametrize(
    ("string_table", "expected_result"),
    [
        pytest.param(
            __section,
            [
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "192.168.10.11",
                        "device": "ASUS USB-AC68 USB Wireless adapter",
                    },
                    inventory_columns={
                        "type": "ipv4",
                        "network": "192.168.10.0",
                        "netmask": "255.255.255.0",
                        "prefixlength": 24,
                        "broadcast": "192.168.10.255",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "169.254.0.1",
                        "device": "VMware Virtual Ethernet Adapter for VMnet1",
                    },
                    inventory_columns={},
                    status_columns={
                        "type": "ipv4",
                        "network": "169.254.0.0",
                        "netmask": "255.255.0.0",
                        "prefixlength": 16,
                        "broadcast": "169.254.255.255",
                    },
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "192.168.1.100",
                        "device": "VMware Virtual Ethernet Adapter for VMnet1",
                    },
                    inventory_columns={
                        "type": "ipv4",
                        "network": "192.168.1.0",
                        "netmask": "255.255.255.0",
                        "prefixlength": 24,
                        "broadcast": "192.168.1.255",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "fe80::5669:a1eb:3add:e9b2",
                        "device": "VMware Virtual Ethernet Adapter for VMnet1",
                    },
                    inventory_columns={},
                    status_columns={
                        "type": "ipv6",
                        "network": "fe80::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                    },
                ),
            ],
            id="inventory_win_ip_address_01",
        ),
    ],
)
def test_inventory_win_ip_address(
    string_table: StringTable,
    expected_result: InventoryResult,
    request: pytest.FixtureRequest,
) -> None:
    section = parse_win_networkadapter(string_table)
    assert list(inventorize_ip_addresses_windows(section)) == expected_result, (
        f"in param {request.node.callspec.id}"
    )


@pytest.mark.parametrize(
    ("string_table", "expected_result"),
    [
        pytest.param(
            __section,
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
            id="host_label_win_ip_address_01",
        ),
    ],
)
def test_host_label_win_ip_address(
    string_table: StringTable,
    expected_result: HostLabelGenerator,
    request: pytest.FixtureRequest,
) -> None:
    section = parse_win_networkadapter(string_table)
    assert list(host_label_win_ip_address(section)) == list(expected_result), (
        f"in param {request.node.callspec.id}"
    )


@pytest.mark.parametrize(
    ("string_table", "expected_inet6"),
    [
        pytest.param(
            [
                ["AdapterType", " Ethernet 802.3"],
                ["MACAddress", " AA", "BB", "CC", "DD", "EE", "FF"],
                ["Name", " Adapter1"],
                ["Speed", " 1000000000"],
                ["Address", " 192.168.1.1 2001:db8::1"],
                ["Subnet", " 255.255.255.0 64"],
                ["Parameters", ""],
            ],
            [AugmentedIPv6Interface("2001:db8::1/64", is_temporary=False)],
            id="parameters_empty",
        ),
        pytest.param(
            [
                ["AdapterType", " Ethernet 802.3"],
                ["MACAddress", " AA", "BB", "CC", "DD", "EE", "FF"],
                ["Name", " Adapter1"],
                ["Speed", " 1000000000"],
                ["Address", " 192.168.1.1 2001:db8::1"],
                ["Subnet", " 255.255.255.0 64"],
                ["Parameters", "2001:db8::1 RouterAdvertisement Random"],
            ],
            [AugmentedIPv6Interface("2001:db8::1/64", is_temporary=True)],
            id="parameters_single",
        ),
        pytest.param(
            [
                ["AdapterType", " Ethernet 802.3"],
                ["MACAddress", " AA", "BB", "CC", "DD", "EE", "FF"],
                ["Name", " Adapter1"],
                ["Speed", " 1000000000"],
                ["Address", " 192.168.1.1 2001:db8::1 2001:db8::2"],
                ["Subnet", " 255.255.255.0 64 64"],
                ["Parameters", "2001:db8::1 RouterAdvertisement Random,2001:db8::2 WellKnown Link"],
            ],
            [
                AugmentedIPv6Interface("2001:db8::1/64", is_temporary=True),
                AugmentedIPv6Interface("2001:db8::2/64", is_temporary=False),
            ],
            id="parameters_multiple",
        ),
    ],
)
def test_parse_win_networkadapter_parameters(
    string_table: StringTable,
    expected_inet6: list[AugmentedIPv6Interface],
) -> None:
    [adapter] = list(parse_win_networkadapter(string_table))
    assert adapter.inet6 == expected_inet6


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just set _PYTEST_RAISES=1 and run this file from your IDE and dive into the code.
    source_file_path = (
        (base := (test_file := Path(__file__)).parents[6])
        / test_file.parent.relative_to(base / "tests/unit")
        / test_file.name[5:]
    ).as_posix()
    assert pytest.main(["--doctest-modules", source_file_path]) in {0, 5}
    pytest.main(["-vvsx", __file__])
