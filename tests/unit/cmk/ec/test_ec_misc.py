#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test different EC standalone helper functions"""

import pytest
from hypothesis import given
from hypothesis.strategies import ip_addresses

from cmk.ec.export import match_ip_network


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


@given(ip_addresses(v=4).map(str))
def test_match_ipv4_network_all_ip(ip: str) -> None:
    """Generated ip ipv4 addresses with network bits added manually"""

    assert match_ip_network(f"{ip}/24", ip) is True
    assert match_ip_network(f"{ip}/0", ip) is True
    assert match_ip_network(ip, f"{ip}/24") is False
    assert match_ip_network(f"{ip}/0", "") is True


@given(ip_addresses(v=6).map(str))
def test_match_ipv6_network_all_ip(ip: str) -> None:
    """Generated ip ipv6 addresses with network bits added manually"""

    assert match_ip_network(f"{ip}/128", ip) is True
    assert match_ip_network(f"{ip}/ffff:ff00::", ip) is False
    assert match_ip_network(f"{ip}/0", ip) is True
    assert match_ip_network(ip, f"{ip}/128") is False
    assert match_ip_network(f"{ip}/0", "") is True
