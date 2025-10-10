#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.huawei_wlc_aps import (
    check_huawei_wlc_aps_cpu,
    check_huawei_wlc_aps_mem,
    check_huawei_wlc_aps_status,
    check_huawei_wlc_aps_temp,
    discovery_huawei_wlc_aps_cpu,
    discovery_huawei_wlc_aps_mem,
    discovery_huawei_wlc_aps_status,
    discovery_huawei_wlc_aps_temp,
    parse_huawei_wlc_aps,
)


def parsed() -> Mapping[str, Any]:
    """Parsed AP data for testing."""
    string_table = [
        [
            ["8", "23", "66", "40", "1"],
            ["4", "0", "0", "255", "0"],
            ["8", "23", "1", "43", "0"],
            ["8", "23", "1", "38", "0"],
            ["8", "23", "1", "38", "0"],
            ["8", "23", "1", "39", "1"],
            ["8", "23", "1", "37", "1"],
            ["8", "23", "1", "38", "0"],
        ],
        [
            ["to-ap-04", "1", "12", "1"],
            ["to-ap-04", "1", "1", "0"],
            ["to-simu", "", "87", "55"],
            ["to-simu", "", "93", "34"],
            ["huawei-test-ap-01", "1", "10", "0"],
            ["huawei-test-ap-01", "1", "7", "0"],
            ["to-ap-02", "1", "13", "0"],
            ["to-ap-02", "1", "1", "0"],
            ["to-ap-06", "1", "89", "0"],
            ["to-ap-06", "1", "1", "0"],
            ["to-ap-03", "1", "13", "2"],
            ["to-ap-03", "1", "1", "0"],
            ["to-ap-05", "1", "13", "0"],
            ["to-ap-05", "1", "1", "0"],
            ["to-ap-01", "1", "12", "0"],
            ["to-ap-01", "1", "1", "0"],
        ],
    ]
    return parse_huawei_wlc_aps(string_table)


def test_huawei_wlc_aps_discovery_status():
    """Test huawei_wlc_aps status discovery."""
    services = list(discovery_huawei_wlc_aps_status(parsed()))

    assert len(services) == 8
    assert sorted(services) == sorted(
        [
            ("huawei-test-ap-01", {}),
            ("to-ap-01", {}),
            ("to-ap-02", {}),
            ("to-ap-03", {}),
            ("to-ap-04", {}),
            ("to-ap-05", {}),
            ("to-ap-06", {}),
            ("to-simu", {}),
        ]
    )


def test_huawei_wlc_aps_discovery_cpu():
    """Test huawei_wlc_aps CPU discovery."""
    services = list(discovery_huawei_wlc_aps_cpu(parsed()))

    assert len(services) == 8
    assert sorted(services) == sorted(
        [
            ("huawei-test-ap-01", {}),
            ("to-ap-01", {}),
            ("to-ap-02", {}),
            ("to-ap-03", {}),
            ("to-ap-04", {}),
            ("to-ap-05", {}),
            ("to-ap-06", {}),
            ("to-simu", {}),
        ]
    )


def test_huawei_wlc_aps_discovery_mem():
    """Test huawei_wlc_aps memory discovery."""
    services = list(discovery_huawei_wlc_aps_mem(parsed()))

    assert len(services) == 8
    assert sorted(services) == sorted(
        [
            ("huawei-test-ap-01", {}),
            ("to-ap-01", {}),
            ("to-ap-02", {}),
            ("to-ap-03", {}),
            ("to-ap-04", {}),
            ("to-ap-05", {}),
            ("to-ap-06", {}),
            ("to-simu", {}),
        ]
    )


def test_huawei_wlc_aps_discovery_temp():
    """Test huawei_wlc_aps temperature discovery."""
    services = list(discovery_huawei_wlc_aps_temp(parsed()))

    assert len(services) == 8
    assert sorted(services) == sorted(
        [
            ("huawei-test-ap-01", {}),
            ("to-ap-01", {}),
            ("to-ap-02", {}),
            ("to-ap-03", {}),
            ("to-ap-04", {}),
            ("to-ap-05", {}),
            ("to-ap-06", {}),
            ("to-simu", {}),
        ]
    )


def test_huawei_wlc_aps_check_status():
    """Test huawei_wlc_aps status check."""
    params = {"levels": (80.0, 90.0)}
    result = list(check_huawei_wlc_aps_status("huawei-test-ap-01", params, parsed()))

    assert len(result) == 8
    # Check AP status
    assert result[0] == (0, "Normal")
    # Check connected users
    assert result[1] == (0, "Connected users: 0")
    # Check 2.4GHz users online with metrics (4-tuple format, not 6-tuple)
    assert result[2] == (0, "Users online [2,4GHz]: 0", [("24ghz_clients", 0, None, None)])
    # Check 2.4GHz radio state
    assert result[3] == (0, "Radio state [2,4GHz]: up")
    # Check 2.4GHz channel usage with metrics (4-tuple format)
    assert result[4] == (
        0,
        "Channel usage [2,4GHz]: 10.00%",
        [("channel_utilization_24ghz", 10.0, 80.0, 90.0)],
    )
    # Check 5GHz users online with metrics
    assert result[5] == (0, "Users online [5GHz]: 0", [("5ghz_clients", 0, None, None)])
    # Check 5GHz radio state
    assert result[6] == (0, "Radio state [5GHz]: up")
    # Check 5GHz channel usage with metrics
    assert result[7] == (
        0,
        "Channel usage [5GHz]: 7.00%",
        [("channel_utilization_5ghz", 7.0, 80.0, 90.0)],
    )


def test_huawei_wlc_aps_check_cpu():
    """Test huawei_wlc_aps CPU check."""
    params = {"levels": (80.0, 90.0)}
    result = list(check_huawei_wlc_aps_cpu("huawei-test-ap-01", params, parsed()))

    assert len(result) == 1
    state, message, metrics = result[0]
    assert state == 0
    assert "Usage: 1.00%" in message
    assert ("cpu_percent", 1.0, 80.0, 90.0) in metrics


def test_huawei_wlc_aps_check_mem():
    """Test huawei_wlc_aps memory check."""
    params = {"levels": (80.0, 90.0)}
    result = list(check_huawei_wlc_aps_mem("huawei-test-ap-01", params, parsed()))

    assert len(result) == 1
    state, message, metrics = result[0]
    assert state == 0
    assert "Used: 23.00%" in message
    assert ("mem_used_percent", 23.0, 80.0, 90.0) in metrics


def test_huawei_wlc_aps_check_temp():
    """Test huawei_wlc_aps temperature check."""
    result = list(check_huawei_wlc_aps_temp("huawei-test-ap-01", {}, parsed()))

    assert len(result) == 1
    state, message = result[0][:2]
    assert state == 0
    assert "43.0 °C" in message


def test_huawei_wlc_aps_check_temp_invalid():
    """Test huawei_wlc_aps temperature check with invalid value."""
    result = list(check_huawei_wlc_aps_temp("to-simu", {}, parsed()))

    assert len(result) == 1
    state, message = result[0][:2]
    assert state == 0
    assert message == "invalid"
