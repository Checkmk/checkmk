#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test different EC standalone helper functions"""

import ipaddress

import pytest

from cmk.ec.main import allowed_ip, unmap_ipv4_address
from cmk.ec.rule_matcher import match_ip_network

ACCESS_LIST = [
    ipaddress.ip_network("::ffff:8.8.4.4"),
    ipaddress.ip_network("1.1.1.1"),
    ipaddress.ip_network("2002:db00::/24"),
    ipaddress.ip_network("100.100.0.0/24"),
]


@pytest.mark.parametrize(
    "ip,  expected",
    (
        pytest.param(
            ipaddress.ip_address("8.8.4.4"),
            True,
            id="IPv4 should be found even if mapped in the list",
        ),
        pytest.param(
            ipaddress.ip_address("::ffff:1.1.1.1"),
            True,
            id="IPv6 mapped should be found even if stored as IPv4 in the list",
        ),
        pytest.param(
            ipaddress.ip_address("::ffff:1.1.1.2"),
            False,
            id="Not found",
        ),
    ),
)
def test_allowed_ip(ip: ipaddress.IPv6Address | ipaddress.IPv4Address, expected: bool) -> None:
    assert allowed_ip(ip, ACCESS_LIST) == expected
    assert allowed_ip(ip, []) is False


@pytest.mark.parametrize(
    "ip_address,  expected",
    (
        pytest.param(
            "::ffff:8.8.4.4",
            "8.8.4.4",
            id="normal IPv4 mapped IPv6 address",
        ),
        pytest.param(
            "8.8.4.4",
            "8.8.4.4",
            id="normal IPv4 address should be unchanged",
        ),
        pytest.param(
            "2001:db00::1",
            "2001:db00::1",
            id="normal IPv6 address should be unchanged",
        ),
        pytest.param(
            "some_hostname",
            "some_hostname",
            id="hostname should be unchanged",
        ),
    ),
)
def test_unmap_ipv4_address(ip_address: str, expected: str) -> None:
    assert unmap_ipv4_address(ip_address) == expected


@pytest.mark.parametrize(
    "pattern, ip, expected",
    (
        pytest.param(
            "10.10.0.0/24",
            "10.10.0.1",
            True,
            id="normal host in 256 host network",
        ),
        pytest.param(
            "10.10.0.0/24",
            "010.10.0.1",
            False,
            id="Invalid ip never matches",
        ),
        pytest.param(
            "10.10.0.0/32",
            "10.10.0.1/32",
            False,
            id="one host one network",
        ),
        pytest.param(
            "127.0.0.1/24",
            "127.0.0.1",
            True,
            id="network pattern contains hosts (an interface)",
        ),
        pytest.param(
            "10.0.0.0/0",
            "",
            True,
            id="empty ip with network bit 0",
        ),
    ),
)
def test_match_ip_network_ipv4(pattern: str, ip: str, expected: bool) -> None:
    assert match_ip_network(pattern, ip) == expected


@pytest.mark.parametrize(
    "pattern, ip, expected",
    (
        pytest.param(
            "2001:db00::0/24",
            "2001:db00::1",
            True,
            id="normal host",
        ),
        pytest.param(
            "2001:db00::0/24",
            "2001:0db00::1",
            False,
            id="Invalid ip never matches",
        ),
        pytest.param(
            "2001:db00::0/128",
            "2001:db00::1/128",
            False,
            id="one host one network",
        ),
        pytest.param(
            "2001:db00::1/24",
            "2001:db00::1",
            True,
            id="network pattern contains hosts (an interface)",
        ),
        pytest.param(
            "2001:db00::0/0",
            "",
            True,
            id="empty ip with network bit 0",
        ),
    ),
)
def test_match_ip_network_ipv6(pattern: str, ip: str, expected: bool) -> None:
    assert match_ip_network(pattern, ip) == expected


@pytest.mark.parametrize(
    "ip",
    [
        "0.0.0.0",
        "192.31.196.172",
        "192.175.48.84",
        "192.0.2.167",
        "234.99.8.118",
        "90.139.70.255",
        "172.20.82.97",
        "13.150.182.3",
        "151.198.173.150",
    ],
)
def test_match_ipv4_network_all_ip(ip: str) -> None:
    """Generated ip ipv4 addresses with network bits added manually"""
    assert match_ip_network(f"{ip}/24", ip) is True
    assert match_ip_network(f"{ip}/0", ip) is True
    assert match_ip_network(ip, f"{ip}/24") is False
    assert match_ip_network(f"{ip}/0", "") is True


@pytest.mark.parametrize(
    "ip",
    [
        "::1",
        "fc00::5ebc",
        "2001:10::7fa6",
        "2001:db8::b8a",
        "f292:6503:d12a:e2c:b38a:8275:15f9:1b1",
        "6bff:c9bc:afa:37e7:c5ac:bc89:fda4:a706",
        "::",
        "fc00::1d5e",
        "fe80::2499:20b:fd13:be60",
    ],
)
def test_match_ipv6_network_all_ip(ip: str) -> None:
    """Generated ip ipv6 addresses with network bits added manually"""

    assert match_ip_network(f"{ip}/128", ip) is True
    assert match_ip_network(f"{ip}/ffff:ff00::", ip) is False
    assert match_ip_network(f"{ip}/0", ip) is True
    assert match_ip_network(ip, f"{ip}/128") is False
    assert match_ip_network(f"{ip}/0", "") is True
