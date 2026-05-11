#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.ibm.agent_based.ibm_svc_enclosure import (
    check_ibm_svc_enclosure,
    discover_ibm_svc_enclosure,
    parse_ibm_svc_enclosure,
)

# Test data representing typical IBM SVC enclosure status information


@pytest.fixture(name="string_table_normal")
def fixture_string_table_normal() -> StringTable:
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
def fixture_string_table_offline() -> StringTable:
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
def fixture_string_table_control() -> StringTable:
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
def fixture_string_table_multiple() -> StringTable:
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
def fixture_string_table_empty() -> StringTable:
    """Empty string table."""
    return []


def test_parse_ibm_svc_enclosure_normal(string_table_normal: StringTable) -> None:
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


def test_parse_ibm_svc_enclosure_control(string_table_control: StringTable) -> None:
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


def test_parse_ibm_svc_enclosure_empty(string_table_empty: StringTable) -> None:
    """Test parsing of empty string table."""
    result = parse_ibm_svc_enclosure(string_table_empty)
    assert result == {}


def test_parse_ibm_svc_enclosure_multiple(string_table_multiple: StringTable) -> None:
    """Test parsing of multiple enclosures."""
    result = parse_ibm_svc_enclosure(string_table_multiple)
    assert isinstance(result, dict)
    assert len(result) == 2
    assert "1" in result
    assert "6" in result
    assert result["1"]["status"] == "online"
    assert result["6"]["status"] == "degraded"


def test_discover_ibm_svc_enclosure(string_table_normal: StringTable) -> None:
    """Test discovery of IBM SVC enclosures."""
    parsed = parse_ibm_svc_enclosure(string_table_normal)
    result = list(discover_ibm_svc_enclosure(parsed))
    assert result == [Service(item="6")]


def test_discover_ibm_svc_enclosure_multiple(
    string_table_multiple: StringTable,
) -> None:
    """Test discovery of multiple enclosures."""
    parsed = parse_ibm_svc_enclosure(string_table_multiple)
    result = list(discover_ibm_svc_enclosure(parsed))
    expected = [Service(item="1"), Service(item="6")]
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected, key=lambda s: s.item or ""
    )


def test_discover_ibm_svc_enclosure_empty(string_table_empty: StringTable) -> None:
    """Test discovery with empty data."""
    parsed = parse_ibm_svc_enclosure(string_table_empty)
    result = list(discover_ibm_svc_enclosure(parsed))
    assert result == []


def test_check_ibm_svc_enclosure_online(string_table_normal: StringTable) -> None:
    """Test check function with online enclosure."""
    parsed = parse_ibm_svc_enclosure(string_table_normal)
    result = list(check_ibm_svc_enclosure("6", {}, parsed))

    assert len(result) == 5

    assert result[0] == Result(state=State.OK, summary="Status: online")
    assert result[1] == Result(state=State.OK, summary="Online canisters: 2 of 2")
    assert result[2] == Result(state=State.OK, summary="Online PSUs: 2 of 2")
    assert result[3] == Result(state=State.OK, summary="Online fan modules: 0 of 0")
    assert result[4] == Result(state=State.OK, summary="Online secondary expander modules: 0 of 0")


def test_check_ibm_svc_enclosure_offline(string_table_offline: StringTable) -> None:
    """Test check function with offline enclosure."""
    parsed = parse_ibm_svc_enclosure(string_table_offline)
    result = list(check_ibm_svc_enclosure("6", {}, parsed))

    assert result[0] == Result(state=State.CRIT, summary="Status: offline")

    # 1 of 2 canisters online, default levels = (total, total) = (2, 2) → CRIT
    assert isinstance(result[1], Result)
    assert result[1].state == State.CRIT
    assert "Online canisters: 1" in result[1].summary
    assert "of 2" in result[1].summary

    # 1 of 2 PSUs online, default levels = (2, 2) → CRIT
    assert isinstance(result[2], Result)
    assert result[2].state == State.CRIT
    assert "Online PSUs: 1" in result[2].summary
    assert "of 2" in result[2].summary


def test_check_ibm_svc_enclosure_control(string_table_control: StringTable) -> None:
    """Test check function with control enclosure."""
    parsed = parse_ibm_svc_enclosure(string_table_control)
    result = list(check_ibm_svc_enclosure("1", {}, parsed))

    assert len(result) >= 3

    assert result[0] == Result(state=State.OK, summary="Status: online")
    assert result[1] == Result(state=State.OK, summary="Online canisters: 2 of 2")


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
    params: dict[str, tuple[int, int]] = {
        "levels_lower_online_canisters": (2, 1),  # warn at 2, crit at 1
    }

    result = list(check_ibm_svc_enclosure("6", params, parsed))

    assert result[0] == Result(state=State.OK, summary="Status: online")
    # 3 online >= 2 warn threshold → OK
    assert result[1] == Result(state=State.OK, summary="Online canisters: 3 of 4")


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
    string_table_multiple: StringTable,
) -> None:
    """Test check function with degraded enclosure status."""
    parsed = parse_ibm_svc_enclosure(string_table_multiple)
    result = list(check_ibm_svc_enclosure("6", {}, parsed))

    assert result[0] == Result(state=State.CRIT, summary="Status: degraded")

    # 1 of 2 canisters online, default levels = (2, 2) → CRIT
    assert isinstance(result[1], Result)
    assert result[1].state == State.CRIT
    assert "Online canisters: 1" in result[1].summary
    assert "of 2" in result[1].summary
