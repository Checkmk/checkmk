#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.plugins.collection.agent_based.keepalived import hex2ip


@pytest.mark.parametrize(
    "hex_input,expected",
    [
        ("C0 A8 01 01", "192.168.1.1"),
        ("c0a80101", "192.168.1.1"),
        ("20 01 0D B8 00 00 00 00 00 00 00 00 00 00 00 01", "2001:db8::1"),
        ("20010DB8000000000000000000000001", "2001:db8::1"),
        ("00 00 00 00", "0.0.0.0"),
        ("ff ff ff ff", "255.255.255.255"),
        ("FFFF0000000000000000000000000001", "ffff::1"),
    ],
)
def test_hex2ip_valid_ip_parsing(hex_input, expected):
    assert hex2ip(hex_input) == expected


def test_hex2ip_uppercase_ipv6():
    hex_input = "20 01 0D B8 00 00 00 00 00 00 00 00 00 00 00 01"
    assert hex2ip(hex_input.upper()) == "2001:db8::1"


@pytest.mark.parametrize(
    "hex_input",
    [
        "GG HH II JJ",  # Invalid hex characters
        "123",  # 1.5 bytes — invalid
        "AA BB CC DD EE",  # Not 4 or 16 bytes
        "20010db800000000000000000000",  # 14 bytes instead of 16
        "ZZ ZZ ZZ ZZ",  # Not hex but valid length
        "",  # Empty string
    ],
)
def test_hex2ip_error_cases(hex_input):
    with pytest.raises(ValueError):
        hex2ip(hex_input)
