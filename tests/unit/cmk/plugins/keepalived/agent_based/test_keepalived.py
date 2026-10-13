#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.keepalived.agent_based.keepalived import (
    check_keepalived,
    discover_keepalived,
    hex2ip,
    parse_keepalived,
    SECTION,
)


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
def test_hex2ip_valid_ip_parsing(hex_input: str, expected: str) -> None:
    assert hex2ip(hex_input) == expected


def test_hex2ip_uppercase_ipv6() -> None:
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
def test_hex2ip_error_cases(hex_input: str) -> None:
    with pytest.raises(ValueError):
        hex2ip(hex_input)


def _raw_address(hex_addr: str) -> str:
    return bytes.fromhex(hex_addr).decode("latin-1")


_PARAMS = {"master": 0, "unknown": 3, "init": 0, "backup": 0, "fault": 2}


def test_parse_keepalived_instance_without_vip() -> None:
    # Regression test for SUP-30143: a vrrp_instance without any configured
    # virtual IP (e.g. keepalived only used to trigger a failover script) leaves
    # the address table without a matching row for that instance.
    string_table = [
        [["VI_1", "2", "1"]],
        [],
    ]
    assert parse_keepalived(string_table) == {"VI_1": ("2", [])}


def test_parse_keepalived_correlates_by_index_not_position() -> None:
    # Two instances, only the second one has a configured VIP. The address
    # table row is listed before the instance rows to prove the match is done
    # via the SNMP index (OIDEnd), not row position.
    string_table = [
        [["VI_1", "2", "1"], ["VI_2", "1", "2"]],
        [["2.1", _raw_address("c0a80101")]],
    ]
    assert parse_keepalived(string_table) == {
        "VI_1": ("2", []),
        "VI_2": ("1", ["192.168.1.1"]),
    }


def test_parse_keepalived_multiple_addresses_for_one_instance() -> None:
    string_table = [
        [["VI_1", "2", "1"]],
        [["1.1", _raw_address("c0a80101")], ["1.2", _raw_address("c0a80102")]],
    ]
    assert parse_keepalived(string_table) == {
        "VI_1": ("2", ["192.168.1.1", "192.168.1.2"]),
    }


def test_discover_keepalived() -> None:
    section = {"VI_1": ("2", []), "VI_2": ("1", ["192.168.1.1"])}
    assert list(discover_keepalived(section)) == [Service(item="VI_1"), Service(item="VI_2")]


def test_check_keepalived_without_vip_does_not_crash() -> None:
    # Regression test for SUP-30143: this used to raise
    # IndexError: list index out of range.
    section: SECTION = {"VI_1": ("2", [])}
    assert list(check_keepalived("VI_1", _PARAMS, section)) == [
        Result(state=State.OK, summary="This node is master.")
    ]


def test_check_keepalived_with_address() -> None:
    section = {"VI_1": ("2", ["192.168.1.1"])}
    assert list(check_keepalived("VI_1", _PARAMS, section)) == [
        Result(state=State.OK, summary="This node is master. IP Address: 192.168.1.1")
    ]


def test_check_keepalived_item_not_found() -> None:
    assert list(check_keepalived("VI_1", _PARAMS, {})) == [
        Result(state=State.UNKNOWN, summary="Item not found in output")
    ]
