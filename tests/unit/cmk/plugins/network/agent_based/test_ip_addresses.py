#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Sequence
from ipaddress import (
    IPv4Interface,
    IPv6Interface,
)

import pytest

from cmk.agent_based.v2 import (
    HostLabel,
    HostLabelGenerator,
    InventoryResult,
    StringByteTable,
    TableRow,
)
from cmk.plugins.network.agent_based.ip_addresses import (
    host_label_ip_addresses,
    inventorize_ip_addresses,
    parse_ip_addresses,
    Section,
)

__broken = [
    [
        "1.4w.10.10.10.230",  # OID end -> type: ipv4, length: 4, ipv4 address
        [],  # ip address -> empty
        "3",  # interface index
        ".1.3.6.1.2.1.4.32.1.5.3.1.4.10.10.10.228.30",  # prefix -> last number (30)
    ],
]
__ip_info_34_ios = [
    [
        "1.4.10.10.10.230",  # OID end -> type: ipv4, length: 4, ipv4 address
        [],  # ip address -> empty
        "3",  # interface index
        ".1.3.6.1.2.1.4.32.1.5.3.1.4.10.10.10.228.30",  # prefix -> last number (30)
    ],
    [
        "2.16.42.0.28.160.16.0.1.53.0.0.0.0.0.0.0.2",  # OID end -> type: ipv6, length: 16, ipv6 address
        [],
        "3",
        ".1.3.6.1.2.1.4.32.1.5.3.2.16.42.0.28.160.16.0.1.53.0.0.0.0.0.0.0.0.64",
    ],
    [
        "4.20.254.128.0.0.0.0.0.0.114.219.152.255.254.159.41.2.18.0.0.8",
        # OID end -> type: ipv6z, length: 20, ipv6 address with interface identifier (18.0.0.8)
        [],
        "3",
        ".0.0",
    ],
]
__ip_info_34_ibm = [
    [
        # OID end -> type: ipv4=1, length=15, ipv4 address
        ".".join(("1.15", *map(str, map(ord, "010.140.160.017")))),
        [],
        "805306370",
        ".0.0",
    ],
    [
        # OID end -> type: ipv6=2, length=39, ipv6 address
        ".".join(("2.39", *map(str, map(ord, "0000:0000:0000:0000:0000:0000:0000:0001")))),
        [],
        "805306371",
        ".0.0",
    ],
]
__ip_info_34_firepower = [
    [
        "1.10.1.1.2",  # OID end -> type: ipv4, , ipv4 address ('10.1.1.2')
        [10, 1, 1, 2],  # ip address in dec bytes
        "18",
        ".1.3.6.1.2.1.4.32.1.5.18.1.10.1.1.0.24",
    ],
    [
        "2.253.0.0.0.0.0.0.1.0.0.0.0.0.0.0.1",
        # OID end -> type: ipv6, ipv6 address ('253.0.0.0.0.0.0.1.0.0.0.0.0.0.0.1')
        [253, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],  # ip address in dec bytes
        "4",
        ".1.3.6.1.2.1.4.32.1.5.4.2.253.0.0.0.0.0.0.1.0.0.0.0.0.0.0.0.64",
    ],
]
__ip_info_34_fortinet = [
    [
        "1.10.118.132.1.76",  # OID end -> type: ipv4, ipv4 address (10.118.132.1), interface index (76)
        [],
        "76",
        ".0.0.0",  # prefix -> missing
    ],
    [
        "2.10762.22982.8208.4113.0.0.0.282.40",
        # OID end -> type: ipv6, ipv6 address (10762.22982.8208.4113.0.0.0.282), interface index (76)
        [],
        "40",
        ".0.0.0",  # prefix -> missing
    ],
]
__ip_info_34_fortinet_2 = [
    [
        "1.4.10.86.60.1.16",
        [],
        "16",
        ".1.3.6.1.2.1.4.32.1.5.16.1.10.86.60.0.27",
    ],
    [
        "2.16.254.128.0.0.0.0.0.0.2.0.94.254.81.92.98.50.20",
        [],
        "20",
        ".1.3.6.1.2.1.4.32.1.5.20.2.254.128.0.0.0.0.0.0.0.0.0.0.0.0.0.0.64",
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            (
                [("12.12.12.1", "if_index1", "3")],
                __ip_info_34_ios,
                [("name1", 23), ("name2", 42)],
            ),
            [
                {"3": IPv4Interface("10.10.10.230/30")},
                {"3": IPv6Interface("2a00:1ca0:1000:135::2/64")},
                {"3": IPv6Interface("fe80::72db:98ff:fe9f:2902%12.00.00.08/64")},
                {"if_index1": IPv4Interface("12.12.12.1/3")},
            ],
        ),
        (
            (
                [("12.12.12.1", "if_index1", "3")],
                __ip_info_34_ibm,
                [("name1", 23), ("name2", 42)],
            ),
            [{"if_index1": IPv4Interface("12.12.12.1/3")}],
        ),
        (
            (
                [("12.12.12.1", "if_index1", "3")],
                __ip_info_34_firepower,
                [("name1", 23), ("name2", 42)],
            ),
            [
                {"18": IPv4Interface("10.1.1.2/24")},
                {"4": IPv6Interface("fd00:0:0:1::1/64")},
                {"if_index1": IPv4Interface("12.12.12.1/3")},
            ],
        ),
        (
            (
                [("12.12.12.1", "if_index1", "3")],
                __ip_info_34_fortinet,
                [("name1", 23), ("name2", 42)],
            ),
            [{"if_index1": IPv4Interface("12.12.12.1/3")}],
        ),
        (
            (
                [("12.12.12.1", "if_index1", "3")],
                __ip_info_34_fortinet_2,
                [("name1", 23), ("name2", 42)],
            ),
            [
                {"16": IPv4Interface("10.86.60.1/27")},
                {"20": IPv6Interface("fe80::200:5efe:515c:6232/64")},
                {"if_index1": IPv4Interface("12.12.12.1/3")},
            ],
        ),
        (
            (
                [["87.65.43.210", "1", "255.255.255.0"]],
                [["", [], "", ""]],  # this happens if threre's no '34' entry
                [["", ""]],
            ),
            [
                {"1": IPv4Interface("87.65.43.210/24")},
            ],
        ),
    ],
)
def test_parse_ip_addresses(
    string_table: Sequence[StringByteTable], expected_result: Section
) -> None:
    assert parse_ip_addresses(string_table) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (None, []),
        (
            (
                {"16": IPv4Interface("10.86.60.1/27")},
                {"20": IPv6Interface("fe80::200:5efe:515c:6232/64")},
                {"if_index1": IPv4Interface("12.12.12.1/3")},
            ),
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
        ),
    ],
)
def test_host_label_ip_addresses(section: Section, expected_result: HostLabelGenerator) -> None:
    assert list(host_label_ip_addresses(section)) == list(expected_result)


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (None, []),
        (
            (
                {"16": IPv4Interface("10.86.60.1/27")},
                {"20": IPv6Interface("fe80::200:5efe:515c:6232/64")},
                {"if_index1": IPv4Interface("12.12.12.1/3")},
            ),
            [
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "10.86.60.1", "device": "16"},
                    inventory_columns={
                        "broadcast": "10.86.60.31",
                        "prefixlength": 27,
                        "netmask": "255.255.255.224",
                        "network": "10.86.60.0",
                        "type": "ipv4",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "fe80::200:5efe:515c:6232", "device": "20"},
                    inventory_columns={
                        "broadcast": "fe80::ffff:ffff:ffff:ffff",
                        "prefixlength": 64,
                        "netmask": "ffff:ffff:ffff:ffff::",
                        "network": "fe80::",
                        "type": "ipv6",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={"address": "12.12.12.1", "device": "if_index1"},
                    inventory_columns={
                        "broadcast": "31.255.255.255",
                        "prefixlength": 3,
                        "netmask": "224.0.0.0",
                        "network": "0.0.0.0",
                        "type": "ipv4",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventorize_ip_addresses(section: Section, expected_result: InventoryResult) -> None:
    assert list(inventorize_ip_addresses(section)) == expected_result
