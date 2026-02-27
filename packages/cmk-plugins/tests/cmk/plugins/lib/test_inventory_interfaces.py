#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

from cmk.agent_based.v2 import (
    InventoryResult,
    TableRow,
)
from cmk.plugins.lib.interfaces import (
    AugmentedIPv4Interface,
    AugmentedIPv6Interface,
    IPNetworkAdapter,
)
from cmk.plugins.lib.inventory_interfaces import inventorize_ip_addresses


@pytest.mark.parametrize(
    ("section", "expected_result"),
    [
        pytest.param(
            [
                IPNetworkAdapter(
                    name="ens32",
                    inet4=[AugmentedIPv4Interface("192.168.10.144/24")],
                    inet6=[AugmentedIPv6Interface("fe80::20c:29ff:fe82:fd72/64")],
                ),
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
            ],
            [
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "192.168.10.144", "device": "ens32"},
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
                    key_columns={"address": "fe80::20c:29ff:fe82:fd72", "device": "ens32"},
                    inventory_columns={
                        "type": "ipv6",
                        "network": "fe80::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "127.0.0.1", "device": "lo"},
                    inventory_columns={
                        "type": "ipv4",
                        "network": "127.0.0.0",
                        "netmask": "255.0.0.0",
                        "prefixlength": 8,
                        "broadcast": "127.255.255.255",
                    },
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "::1", "device": "lo"},
                    inventory_columns={
                        "type": "ipv6",
                        "network": "::1",
                        "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                        "prefixlength": 128,
                        "broadcast": "::1",
                    },
                    status_columns={},
                ),
            ],
            id="inventory_ip_addresses_01",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="16",
                    inet4=[AugmentedIPv4Interface("10.86.60.1/24")],
                    inet6=[AugmentedIPv6Interface("fe80::200:5efe:515c:6232/64")],
                ),
                IPNetworkAdapter(
                    name="20",
                    inet6=[AugmentedIPv6Interface("fe80::200:5efe:515c:6232/64")],
                ),
                IPNetworkAdapter(
                    name="if_index1",
                    inet4=[AugmentedIPv4Interface("12.12.12.1/24")],
                ),
            ],
            [
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "10.86.60.1", "device": "16"},
                    inventory_columns={
                        "type": "ipv4",
                        "network": "10.86.60.0",
                        "netmask": "255.255.255.0",
                        "prefixlength": 24,
                        "broadcast": "10.86.60.255",
                    },
                    status_columns={},
                ),
                TableRow(  # duplicate?
                    path=["networking", "addresses"],
                    key_columns={"address": "fe80::200:5efe:515c:6232", "device": "16"},
                    inventory_columns={
                        "type": "ipv6",
                        "network": "fe80::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "fe80::200:5efe:515c:6232", "device": "20"},
                    inventory_columns={
                        "type": "ipv6",
                        "network": "fe80::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "12.12.12.1", "device": "if_index1"},
                    inventory_columns={
                        "type": "ipv4",
                        "network": "12.12.12.0",
                        "netmask": "255.255.255.0",
                        "prefixlength": 24,
                        "broadcast": "12.12.12.255",
                    },
                    status_columns={},
                ),
            ],
            id="inventory_ip_addresses_02",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="ASUS USB-AC68 USB Wireless adapter",
                    inet4=[AugmentedIPv4Interface("192.168.10.11/24")],
                ),
                IPNetworkAdapter(
                    name="ASUS USB-AC68 USB Wireless adapter",
                    inet4=[AugmentedIPv4Interface("192.168.10.11/24")],
                ),
                IPNetworkAdapter(
                    name="Bluetooth Device (Personal Area Network)",
                ),
                IPNetworkAdapter(
                    name="Microsoft Wi-Fi Direct Virtual Adapter",
                ),
                IPNetworkAdapter(
                    name="Microsoft Wi-Fi Direct Virtual Adapter #2",
                ),
                IPNetworkAdapter(
                    name="VMware Virtual Ethernet Adapter for VMnet1",
                    inet4=[
                        AugmentedIPv4Interface("169.254.0.1/16"),
                        AugmentedIPv4Interface("192.168.1.100/24"),
                    ],
                    inet6=[AugmentedIPv6Interface("fe80::5669:a1eb:3add:e9b2/64")],
                ),
            ],
            [
                TableRow(  # duplicate?
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
                    inventory_columns={
                        "type": "ipv4",
                        "network": "169.254.0.0",
                        "netmask": "255.255.0.0",
                        "prefixlength": 16,
                        "broadcast": "169.254.255.255",
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
                    inventory_columns={
                        "type": "ipv6",
                        "network": "fe80::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                    },
                    status_columns={},
                ),
            ],
            id="inventory_ip_addresses_03",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="wlp9s0",
                    inet4=[
                        AugmentedIPv4Interface("192.168.1.189/24"),
                    ],
                    inet6=[
                        AugmentedIPv6Interface("2a00:6020:4083:f400:91db:40b7:c583:4591/64"),
                        AugmentedIPv6Interface("2a00:6020:4083:f400:7f25:1049:d74b:39e/64"),
                        AugmentedIPv6Interface("fe80::99d8:98c7:1073:f235/64"),
                    ],
                ),
            ],
            [
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "192.168.1.189", "device": "wlp9s0"},
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
                        "address": "2a00:6020:4083:f400:91db:40b7:c583:4591",
                        "device": "wlp9s0",
                    },
                    inventory_columns={
                        "type": "ipv6",
                        "network": "2a00:6020:4083:f400::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "2a00:6020:4083:f400:ffff:ffff:ffff:ffff",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "address": "2a00:6020:4083:f400:7f25:1049:d74b:39e",
                        "device": "wlp9s0",
                    },
                    inventory_columns={
                        "type": "ipv6",
                        "network": "2a00:6020:4083:f400::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "2a00:6020:4083:f400:ffff:ffff:ffff:ffff",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "fe80::99d8:98c7:1073:f235", "device": "wlp9s0"},
                    inventory_columns={
                        "type": "ipv6",
                        "network": "fe80::",
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "prefixlength": 64,
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                    },
                    status_columns={},
                ),
            ],
            id="inventory_ip_addresses_04",
        ),
    ],
)
def test_inventorize_ip_addresses(
    section: Iterable[IPNetworkAdapter],
    expected_result: InventoryResult,
    request: pytest.FixtureRequest,
) -> None:
    assert list(inventorize_ip_addresses(section)) == list(expected_result), (
        f"in param {request.node.callspec.id}"
    )


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just set _PYTEST_RAISES=1 and run this file from your IDE and dive into the code.
    source_file_path = (
        (base := (test_file := Path(__file__)).parents[4])
        / test_file.parent.relative_to(base / "tests")
        / test_file.name[5:]
    ).as_posix()
    assert pytest.main(["--doctest-modules", source_file_path]) in {0, 5}
    pytest.main(["-vvsx", *sys.argv[1:], __file__])
