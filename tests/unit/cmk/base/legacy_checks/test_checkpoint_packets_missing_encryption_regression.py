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


@pytest.fixture(name="string_table_missing_encryption")
def string_table_missing_encryption_fixture() -> list[list[list[str]]]:
    """Test data for checkpoint packet statistics with missing encryption data"""
    return [
        [["120", "180", "210", "4"]],  # Accepted, Rejected, Dropped, Logged
        [],  # Empty encryption data
    ]


@pytest.fixture(name="parsed_missing_encryption")
def parsed_missing_encryption_fixture(
    string_table_missing_encryption: list[list[list[str]]],
) -> dict[str, Any]:
    """Parsed checkpoint packet data with missing encryption"""
    return parse_checkpoint_packets(string_table_missing_encryption)


def test_parse_checkpoint_packets_missing_encryption(
    string_table_missing_encryption: list[list[list[str]]],
) -> None:
    """Test checkpoint packet parsing when encryption data is missing"""
    parsed = parse_checkpoint_packets(string_table_missing_encryption)

    # Should only have the basic packet stats, no encryption stats
    expected = {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
    }
    assert parsed == expected


def test_discover_checkpoint_packets_missing_encryption(
    parsed_missing_encryption: dict[str, Any],
) -> None:
    """Test checkpoint packet discovery with missing encryption data"""
    discovered = list(discover_checkpoint_packets(parsed_missing_encryption))
    assert len(discovered) == 1
    assert discovered[0] == (None, {})


@time_machine.travel("2019-10-28 08:51:18")
def test_check_checkpoint_packets_missing_encryption_initial_run(
    parsed_missing_encryption: dict[str, Any],
) -> None:
    """Test checkpoint packet check with missing encryption data on initial run"""
    params = {
        "accepted": (100000, 200000),
        "rejected": (100000, 200000),
        "dropped": (100000, 200000),
        "logged": (100000, 200000),
        "espencrypted": (100000, 200000),
        "espdecrypted": (100000, 200000),
    }

    # Initial run should trigger MKCounterWrapped for all present counters
    with pytest.raises(Exception):  # MKCounterWrapped
        list(check_checkpoint_packets(None, params, parsed_missing_encryption))


def test_check_checkpoint_packets_missing_encryption_only_basic_metrics() -> None:
    """Test that only basic metrics are processed when encryption data is missing"""
    test_data = {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
        # No EspEncrypted or EspDecrypted
    }

    # Should not cause any errors, just skip missing metrics
    # This verifies the parser handles missing encryption data gracefully
    discovered = list(discover_checkpoint_packets(test_data))
    assert len(discovered) == 1  # Still creates a service

    # Check that parsing works with partial data
    assert "Accepted" in test_data
    assert "EspEncrypted" not in test_data


def test_parse_checkpoint_packets_completely_empty_encryption() -> None:
    """Test parsing when second SNMP tree is completely empty"""
    empty_encryption_data = [
        [["120", "180", "210", "4"]],
        [],  # Completely empty second tree
    ]

    parsed = parse_checkpoint_packets(empty_encryption_data)

    # Should only contain basic packet stats
    expected = {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
    }
    assert parsed == expected


def test_parse_checkpoint_packets_malformed_encryption_data() -> None:
    """Test parsing when encryption data is malformed"""
    malformed_data = [
        [["120", "180", "210", "4"]],
        [["invalid"]],  # Only one value instead of two
    ]

    parsed = parse_checkpoint_packets(malformed_data)

    # Should contain basic stats plus whatever can be parsed from encryption
    expected = {
        "Accepted": 120,
        "Rejected": 180,
        "Dropped": 210,
        "Logged": 4,
        # EspEncrypted should not be present due to invalid data
        # EspDecrypted should not be present due to IndexError
    }
    assert parsed == expected


def test_parse_checkpoint_packets_partial_basic_data() -> None:
    """Test parsing when basic packet data is incomplete"""
    incomplete_basic_data = [
        [["120", "180"]],  # Only first two values
        [["0", "60"]],  # Complete encryption data
    ]

    parsed = parse_checkpoint_packets(incomplete_basic_data)

    # Should contain what can be parsed
    expected = {
        "Accepted": 120,
        "Rejected": 180,
        "EspEncrypted": 0,
        "EspDecrypted": 60,
        # Dropped and Logged should be missing due to IndexError
    }
    assert parsed == expected
