#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.fortigate_sslvpn import (
    check_fortigate_sslvpn,
    discover_fortigate_sslvpn,
    parse_fortigate_sslvpn,
)


@pytest.fixture(name="string_table")
def _string_table() -> list[list[list[str]]]:
    return [[["root"]], [["2", "9", "6", "6", "20"]]]


@pytest.fixture(name="parsed")
def _parsed(string_table: list[list[list[str]]]) -> Mapping[str, Any]:
    return parse_fortigate_sslvpn(string_table)


def test_parse_fortigate_sslvpn(string_table: list[list[list[str]]]) -> None:
    result = parse_fortigate_sslvpn(string_table)

    expected = {
        "root": {
            "state": "2",
            "users": 9,
            "web_sessions": 6,
            "tunnels": 6,
            "tunnels_max": 20,
        }
    }

    assert result == expected


def test_discover_fortigate_sslvpn(parsed: Mapping[str, Any]) -> None:
    result = list(discover_fortigate_sslvpn(parsed))
    assert result == [("root", {})]


def test_check_fortigate_sslvpn_thresholds(parsed: Mapping[str, Any]) -> None:
    params = {
        "tunnel_levels": (4, 7)  # Only tunnels support thresholds
    }
    result = list(check_fortigate_sslvpn("root", params, parsed))

    assert len(result) == 4

    # Check enabled state
    assert result[0][0] == 0  # OK state
    assert "enabled" in result[0][1]

    # Check users - no thresholds available, always OK
    assert result[1][0] == 0  # OK state
    assert "Users: 9" in result[1][1]
    if len(result[1]) > 2:
        assert result[1][2] == [("active_vpn_users", 9, None, None)]

    # Check web sessions - no thresholds available, always OK
    assert result[2][0] == 0  # OK state
    assert "Web sessions: 6" in result[2][1]
    if len(result[2]) > 2:
        assert result[2][2] == [("active_vpn_websessions", 6, None, None)]

    # Check tunnels with thresholds - should be WARN (6 > 4 but < 7)
    assert result[3][0] == 1  # WARN state
    assert "Tunnels: 6" in result[3][1]
    if len(result[3]) > 2:
        assert result[3][2] == [("active_vpn_tunnels", 6, 4, 7, 0.0, 20.0)]


def test_check_fortigate_sslvpn_with_tunnel_levels(parsed: Mapping[str, Any]) -> None:
    params = {"tunnel_levels": (5, 10)}
    result = list(check_fortigate_sslvpn("root", params, parsed))

    assert len(result) == 4

    # Check enabled state
    assert result[0][0] == 0  # OK state
    assert "enabled" in result[0][1]

    # Check users (no thresholds)
    assert result[1][0] == 0  # OK state
    assert "Users: 9" in result[1][1]

    # Check web sessions (no thresholds)
    assert result[2][0] == 0  # OK state
    assert "Web sessions: 6" in result[2][1]

    # Check tunnels with threshold - should be WARNING (6 > 5)
    assert result[3][0] == 1  # WARNING state
    assert "Tunnels: 6" in result[3][1]
    assert "(warn/crit at 5/10)" in result[3][1]
    assert result[3][2] == [("active_vpn_tunnels", 6, 5, 10, 0.0, 20.0)]


def test_check_fortigate_sslvpn_disabled_state() -> None:
    # Test with disabled state
    string_table = [[["root"]], [["1", "0", "0", "0", "20"]]]
    parsed = parse_fortigate_sslvpn(string_table)

    result = list(check_fortigate_sslvpn("root", {}, parsed))

    assert len(result) == 4

    # Check disabled state
    assert result[0][0] == 0  # OK state
    assert "disabled" in result[0][1]

    # All counters should be 0
    assert "Users: 0" in result[1][1]
    assert "Web sessions: 0" in result[2][1]
    assert "Tunnels: 0" in result[3][1]


def test_check_fortigate_sslvpn_critical_tunnel_levels(parsed: Mapping[str, Any]) -> None:
    params = {"tunnel_levels": (3, 5)}
    result = list(check_fortigate_sslvpn("root", params, parsed))

    # Check tunnels with critical threshold - should be CRITICAL (6 > 5)
    assert result[3][0] == 2  # CRITICAL state
    assert "Tunnels: 6" in result[3][1]
    assert "(warn/crit at 3/5)" in result[3][1]
    assert result[3][2] == [("active_vpn_tunnels", 6, 3, 5, 0.0, 20.0)]


def test_check_fortigate_sslvpn_multiple_domains() -> None:
    # Test with multiple VPN domains
    string_table = [
        [["root"], ["branch1"]],
        [["2", "9", "6", "6", "20"], ["2", "3", "2", "1", "10"]],
    ]
    parsed = parse_fortigate_sslvpn(string_table)

    # Check discovery finds both domains
    discovery_result = list(discover_fortigate_sslvpn(parsed))
    assert len(discovery_result) == 2
    assert ("root", {}) in discovery_result
    assert ("branch1", {}) in discovery_result

    # Check both domains can be monitored
    root_result = list(check_fortigate_sslvpn("root", {}, parsed))
    branch1_result = list(check_fortigate_sslvpn("branch1", {}, parsed))

    assert len(root_result) == 4
    assert len(branch1_result) == 4

    # Verify different values
    assert "Users: 9" in root_result[1][1]
    assert "Users: 3" in branch1_result[1][1]

    assert "Tunnels: 6" in root_result[3][1]
    assert "Tunnels: 1" in branch1_result[3][1]


def test_check_fortigate_sslvpn_missing_item(parsed: Mapping[str, Any]) -> None:
    result = list(check_fortigate_sslvpn("nonexistent", {}, parsed))
    assert result == []


def test_check_fortigate_sslvpn_high_usage_scenario() -> None:
    # Test scenario with high usage approaching limits
    string_table = [[["production"]], [["2", "150", "80", "18", "20"]]]
    parsed = parse_fortigate_sslvpn(string_table)

    params = {"tunnel_levels": (15, 19)}
    result = list(check_fortigate_sslvpn("production", params, parsed))

    assert len(result) == 4

    # Should be WARNING (18 > 15 but < 19)
    assert result[3][0] == 1  # WARNING state
    assert "Tunnels: 18" in result[3][1]
    assert "(warn/crit at 15/19)" in result[3][1]

    # Check high user count
    assert "Users: 150" in result[1][1]
    assert "Web sessions: 80" in result[2][1]


def test_parse_fortigate_sslvpn_empty_data() -> None:
    # Test with empty data
    string_table: list[list[str]] = [[], []]
    result = parse_fortigate_sslvpn(string_table)
    assert result == {}


def test_discover_fortigate_sslvpn_empty_section() -> None:
    # Test discovery with empty section
    result = list(discover_fortigate_sslvpn({}))
    assert result == []
