#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Sequence

import pytest

from cmk.base.legacy_checks.ibm_svc_enclosure import (
    check_ibm_svc_enclosure,
    discover_ibm_svc_enclosure,
    parse_ibm_svc_enclosure,
)

# Test data representing typical IBM SVC enclosure status information


@pytest.fixture(name="string_table_normal")
def fixture_string_table_normal() -> Sequence[Sequence[str]]:
    """Standard IBM SVC enclosure data with expansion enclosure online."""
    return [
        [
            "6",
            "online",
            "expansion",
            "yes",
            "0",
            "io_grp0",
            "2072-24E",
            "7804352",
            "2",
            "2",
            "2",
            "2",
            "24",
            "0",
            "0",
            "0",
            "0",
        ]
    ]


@pytest.fixture(name="string_table_offline")
def fixture_string_table_offline() -> Sequence[Sequence[str]]:
    """IBM SVC enclosure data with offline status."""
    return [
        [
            "6",
            "offline",
            "expansion",
            "yes",
            "0",
            "io_grp0",
            "2072-24E",
            "7804352",
            "2",
            "1",
            "2",
            "1",
            "24",
            "4",
            "3",
            "2",
            "1",
        ]
    ]


@pytest.fixture(name="string_table_control")
def fixture_string_table_control() -> Sequence[Sequence[str]]:
    """IBM SVC control enclosure with fewer columns (legacy format)."""
    return [
        [
            "1",
            "online",
            "control",
            "9843-AE2",
            "6860407",
            "2",
            "2",
            "2",
            "12",
        ]
    ]


@pytest.fixture(name="string_table_multiple")
def fixture_string_table_multiple() -> Sequence[Sequence[str]]:
    """Multiple IBM SVC enclosures with mixed states."""
    return [
        [
            "1",
            "online",
            "control",
            "yes",
            "0",
            "io_grp0",
            "9843-AE2",
            "6860407",
            "2",
            "2",
            "2",
            "2",
            "12",
            "0",
            "0",
            "0",
            "0",
        ],
        [
            "6",
            "degraded",
            "expansion",
            "yes",
            "0",
            "io_grp0",
            "2072-24E",
            "7804352",
            "2",
            "1",
            "2",
            "2",
            "24",
            "4",
            "4",
            "2",
            "2",
        ],
    ]


@pytest.fixture(name="string_table_empty")
def fixture_string_table_empty() -> Sequence[Sequence[str]]:
    """Empty string table."""
    return []


def test_parse_ibm_svc_enclosure_normal(string_table_normal: Sequence[Sequence[str]]) -> None:
    """Test parsing of normal IBM SVC enclosure data."""
    result = parse_ibm_svc_enclosure(string_table_normal)
    assert isinstance(result, dict)
    assert "6" in result
    enclosure = result["6"]
    assert enclosure["status"] == "online"
    assert enclosure["type"] == "expansion"
    assert enclosure["managed"] == "yes"
    assert enclosure["total_canisters"] == "2"
    assert enclosure["online_canisters"] == "2"
    assert enclosure["total_PSUs"] == "2"
    assert enclosure["online_PSUs"] == "2"


def test_parse_ibm_svc_enclosure_control(string_table_control: Sequence[Sequence[str]]) -> None:
    """Test parsing of control enclosure with legacy format."""
    result = parse_ibm_svc_enclosure(string_table_control)
    assert isinstance(result, dict)
    assert "1" in result
    enclosure = result["1"]
    assert enclosure["status"] == "online"
    assert enclosure["type"] == "control"
    assert enclosure["total_canisters"] == "2"
    assert enclosure["online_canisters"] == "2"
    assert enclosure["online_PSUs"] == "2"


def test_parse_ibm_svc_enclosure_empty(string_table_empty: Sequence[Sequence[str]]) -> None:
    """Test parsing of empty string table."""
    result = parse_ibm_svc_enclosure(string_table_empty)
    assert result == {}


def test_parse_ibm_svc_enclosure_multiple(string_table_multiple: Sequence[Sequence[str]]) -> None:
    """Test parsing of multiple enclosures."""
    result = parse_ibm_svc_enclosure(string_table_multiple)
    assert isinstance(result, dict)
    assert len(result) == 2
    assert "1" in result
    assert "6" in result
    assert result["1"]["status"] == "online"
    assert result["6"]["status"] == "degraded"


def test_discover_ibm_svc_enclosure(string_table_normal: Sequence[Sequence[str]]) -> None:
    """Test discovery of IBM SVC enclosures."""
    parsed = parse_ibm_svc_enclosure(string_table_normal)
    result = list(discover_ibm_svc_enclosure(parsed))
    assert result == [("6", {})]


def test_discover_ibm_svc_enclosure_multiple(
    string_table_multiple: Sequence[Sequence[str]],
) -> None:
    """Test discovery of multiple enclosures."""
    parsed = parse_ibm_svc_enclosure(string_table_multiple)
    result = list(discover_ibm_svc_enclosure(parsed))
    expected: list[tuple[str, dict]] = [("1", {}), ("6", {})]
    assert sorted(result) == sorted(expected)


def test_discover_ibm_svc_enclosure_empty(string_table_empty: Sequence[Sequence[str]]) -> None:
    """Test discovery with empty data."""
    parsed = parse_ibm_svc_enclosure(string_table_empty)
    result = list(discover_ibm_svc_enclosure(parsed))
    assert result == []


def test_check_ibm_svc_enclosure_online(string_table_normal: Sequence[Sequence[str]]) -> None:
    """Test check function with online enclosure."""
    parsed = parse_ibm_svc_enclosure(string_table_normal)
    result = list(check_ibm_svc_enclosure("6", {}, parsed))

    # Verify basic structure
    assert len(result) == 5

    # Check status
    status_result = result[0]
    assert status_result[0] == 0  # OK state
    assert "Status: online" in status_result[1]

    # Check canisters
    canister_result = result[1]
    assert canister_result[0] == 0  # OK state
    assert "Online canisters: 2 of 2" in canister_result[1]

    # Check PSUs
    psu_result = result[2]
    assert psu_result[0] == 0  # OK state
    assert "Online PSUs: 2 of 2" in psu_result[1]

    # Check fan modules (0 in this case)
    fan_result = result[3]
    assert fan_result[0] == 0  # OK state
    assert "Online fan modules: 0 of 0" in fan_result[1]

    # Check secondary expander modules
    sem_result = result[4]
    assert sem_result[0] == 0  # OK state
    assert "Online secondary expander modules: 0 of 0" in sem_result[1]


def test_check_ibm_svc_enclosure_offline(string_table_offline: Sequence[Sequence[str]]) -> None:
    """Test check function with offline enclosure."""
    parsed = parse_ibm_svc_enclosure(string_table_offline)
    result = list(check_ibm_svc_enclosure("6", {}, parsed))

    # Check status (should be critical)
    status_result = result[0]
    assert status_result[0] == 2  # CRITICAL state
    assert "Status: offline" in status_result[1]

    # Check degraded components (with default thresholds, 1 of 2 online should be critical)
    canister_result = result[1]
    assert canister_result[0] == 2  # CRITICAL state (1 < 2 total threshold)
    assert "Online canisters: 1" in canister_result[1]
    assert "of 2" in canister_result[1]

    psu_result = result[2]
    assert psu_result[0] == 2  # CRITICAL state (1 < 2 total threshold)
    assert "Online PSUs: 1" in psu_result[1]
    assert "of 2" in psu_result[1]


def test_check_ibm_svc_enclosure_control(string_table_control: Sequence[Sequence[str]]) -> None:
    """Test check function with control enclosure."""
    parsed = parse_ibm_svc_enclosure(string_table_control)
    result = list(check_ibm_svc_enclosure("1", {}, parsed))

    # Should have fewer results due to legacy format
    assert len(result) >= 3

    # Check status
    status_result = result[0]
    assert status_result[0] == 0  # OK state
    assert "Status: online" in status_result[1]

    # Check canisters
    canister_result = result[1]
    assert canister_result[0] == 0  # OK state
    assert "Online canisters: 2 of 2" in canister_result[1]


def test_check_ibm_svc_enclosure_with_thresholds() -> None:
    """Test check function with custom threshold parameters."""
    string_table = [
        [
            "6",
            "online",
            "expansion",
            "yes",
            "0",
            "io_grp0",
            "2072-24E",
            "7804352",
            "4",
            "3",  # 3 of 4 canisters online
            "4",
            "4",  # All PSUs online
            "24",
            "0",
            "0",
            "0",
            "0",
        ]
    ]

    parsed = parse_ibm_svc_enclosure(string_table)
    params = {
        "levels_lower_online_canisters": (2, 1),  # warn at 2, crit at 1
    }

    result = list(check_ibm_svc_enclosure("6", params, parsed))

    # Check status
    status_result = result[0]
    assert status_result[0] == 0  # OK state

    # Check canisters with thresholds (3 online should be OK with warn at 2)
    canister_result = result[1]
    assert canister_result[0] == 0  # OK state
    assert "Online canisters: 3 of 4" in canister_result[1]


def test_check_ibm_svc_enclosure_missing_item() -> None:
    """Test check function with non-existent item."""
    string_table = [
        [
            "6",
            "online",
            "expansion",
            "yes",
            "0",
            "io_grp0",
            "2072-24E",
            "7804352",
            "2",
            "2",
            "2",
            "2",
            "24",
            "0",
            "0",
            "0",
            "0",
        ]
    ]

    parsed = parse_ibm_svc_enclosure(string_table)
    result = list(check_ibm_svc_enclosure("999", {}, parsed))
    assert result == []


def test_check_ibm_svc_enclosure_degraded_status(
    string_table_multiple: Sequence[Sequence[str]],
) -> None:
    """Test check function with degraded enclosure status."""
    parsed = parse_ibm_svc_enclosure(string_table_multiple)
    result = list(check_ibm_svc_enclosure("6", {}, parsed))

    # Check status (degraded should be critical)
    status_result = result[0]
    assert status_result[0] == 2  # CRITICAL state
    assert "Status: degraded" in status_result[1]

    # Check components (1 of 2 canisters should be critical with default thresholds)
    canister_result = result[1]
    assert canister_result[0] == 2  # CRITICAL state (1 < 2 total threshold)
    assert "Online canisters: 1" in canister_result[1]
    assert "of 2" in canister_result[1]
