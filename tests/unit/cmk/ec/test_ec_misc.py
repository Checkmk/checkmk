#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test different EC standalone helper functions"""

import pytest
from hypothesis import given
from hypothesis.strategies import ip_addresses

from cmk.ec.export import match_ipv4_network


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
def test_match_ipv4_network(pattern: str, ip: str, expected: bool) -> None:

    assert match_ipv4_network(pattern, ip) == expected


@pytest.mark.parametrize(
    "pattern, ip",
    (
        pytest.param(
            "127.0.0.x/0",
            "127.0.0.1",
            id="one octet is not decimal",
        ),
        pytest.param(
            "somestring/0",
            "127.0.0.1",
            id="nonsense string with network bit",
        ),
        pytest.param(
            "somestring",
            "127.0.0.1",
            id="nonsense string ",
        ),
        pytest.param(
            "",
            "",
            id="empty pattern",
        ),
        pytest.param(
            "10.10.0.0/x",
            "127.0.0.1",
            id="non-decimal network bit",
        ),
    ),
)
def test_match_ipv4_network_exceptions(pattern: str, ip: str) -> None:

    with pytest.raises(ValueError, match="invalid literal for int"):
        match_ipv4_network(pattern, ip)


@given(ip_addresses(v=4).map(str))
def test_match_ipv4_network_all_ip(ip: str) -> None:
    """Generated ip ipv4 addresses with network bits added manually"""

    assert match_ipv4_network(f"{ip}/24", ip) is True
    assert match_ipv4_network(f"{ip}/0", ip) is True
    assert match_ipv4_network(ip, f"{ip}/24") is False
    assert match_ipv4_network(f"{ip}/0", "") is True
