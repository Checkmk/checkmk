#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest
import time_machine

from cmk.base.legacy_checks.checkpoint_packets import (
    check_checkpoint_packets,
    discover_checkpoint_packets,
    parse_checkpoint_packets,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[list[str]]]:
    """Test data for checkpoint packet statistics"""
    return [
        [["120", "180", "210", "4"]],  # Accepted, Rejected, Dropped, Logged
        [["0", "60"]],  # EspEncrypted, EspDecrypted
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[list[str]]]) -> dict[str, Any]:
    """Parsed checkpoint packet data"""
    return parse_checkpoint_packets(string_table)


def test_parse_checkpoint_packets(string_table: list[list[list[str]]]) -> None:
    """Test checkpoint packet parsing extracts correct values"""
    parsed = parse_checkpoint_packets(string_table)

    expected = {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
        "EspEncrypted": 0,
        "EspDecrypted": 60,
    }
    assert parsed == expected


def test_parse_checkpoint_packets_incomplete_data() -> None:
    """Test checkpoint packet parsing handles incomplete data gracefully"""
    # Missing second array
    incomplete_data = [[["120", "180"]]]
    parsed = parse_checkpoint_packets(incomplete_data)

    # Should only have the values from first array
    expected = {
        "Accepted": 120,
        "Rejected": 180,
    }
    assert parsed == expected


def test_parse_checkpoint_packets_invalid_values() -> None:
    """Test checkpoint packet parsing handles invalid values"""
    invalid_data = [
        [["abc", "180", "210", "4"]],  # Invalid first value
        [["0", "xyz"]],  # Invalid second value
    ]
    parsed = parse_checkpoint_packets(invalid_data)

    # Should skip invalid values
    expected = {
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
        "EspEncrypted": 0,
    }
    assert parsed == expected


def test_discover_checkpoint_packets(parsed: dict[str, Any]) -> None:
    """Test checkpoint packet discovery creates service when data is present"""
    discovered = list(discover_checkpoint_packets(parsed))
    assert len(discovered) == 1
    assert discovered[0] == (None, {})


def test_discover_checkpoint_packets_empty_data() -> None:
    """Test checkpoint packet discovery skips when no data is present"""
    discovered = list(discover_checkpoint_packets({}))
    assert len(discovered) == 0


@time_machine.travel("2019-10-28 08:51:18")
def test_check_checkpoint_packets_initial_run(parsed: dict[str, Any]) -> None:
    """Test checkpoint packet check on initial run (no rates yet)"""
    params = {
        "accepted": (100000, 200000),
        "rejected": (100000, 200000),
        "dropped": (100000, 200000),
        "logged": (100000, 200000),
        "espencrypted": (100000, 200000),
        "espdecrypted": (100000, 200000),
    }

    # Initial run should trigger MKCounterWrapped for all counters
    with pytest.raises(Exception):  # MKCounterWrapped
        list(check_checkpoint_packets(None, params, parsed))


def test_check_checkpoint_packets_empty_parsed() -> None:
    """Test checkpoint packet check with empty parsed data"""
    result = list(check_checkpoint_packets(None, {}, {}))
    assert len(result) == 0  # No results for empty data
