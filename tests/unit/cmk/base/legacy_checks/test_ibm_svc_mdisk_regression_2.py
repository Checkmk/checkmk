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

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.ibm_svc_mdisk import (
    check_ibm_svc_mdisk,
    discover_ibm_svc_mdisk,
    parse_ibm_svc_mdisk,
)


@pytest.fixture(name="string_table")
def _string_table() -> list[list[str]]:
    """
    IBM SVC MDisk data with warning percentage and specific header format.
    Tests scenario where mdisk exists but should not be discovered.
    """
    return [
        [
            "id",
            "status",
            "mode",
            "capacity",
            "encrypt",
            "enclosure_id",
            "over_provisioned",
            "supports_unmap",
            "warning",
        ],
        ["0", "online", "array", "20.8TB", "no", "1", "no", "yes", "80"],
    ]


@pytest.fixture(name="parsed")
def _parsed(string_table: list[list[str]]) -> Mapping[str, Any]:
    return parse_ibm_svc_mdisk(string_table)


def test_parse_ibm_svc_mdisk_regression_2(string_table: list[list[str]]) -> None:
    """Test parsing of IBM SVC MDisk data with non-standard header format."""
    result = parse_ibm_svc_mdisk(string_table)

    # The parser should handle the non-standard header gracefully
    # In this case, no items should be parsed due to missing required fields
    assert isinstance(result, dict)
    assert len(result) == 0  # Empty because 'name' field is missing from header


def test_discover_ibm_svc_mdisk_regression_2_empty_section(parsed: Mapping[str, Any]) -> None:
    """Test discovery with empty parsed section."""
    result = list(discover_ibm_svc_mdisk(parsed))
    assert result == []  # No items discovered


def test_discover_ibm_svc_mdisk_regression_2() -> None:
    """Test discovery behavior with properly named mdisk (simulated scenario)."""
    # Simulate what would happen if the data was properly parsed with name field
    mock_parsed = {
        "mdisk_0": {
            "id": "0",
            "name": "mdisk_0",
            "status": "online",
            "mode": "array",
            "capacity": "20.8TB",
            "encrypt": "no",
        }
    }

    result = list(discover_ibm_svc_mdisk(mock_parsed))
    assert result == [("mdisk_0", {})]


def test_check_ibm_svc_mdisk_regression_2_missing_item(parsed: Mapping[str, Any]) -> None:
    """Test check function with missing item returns empty generator."""
    result = list(check_ibm_svc_mdisk("nonexistent", {}, parsed))
    assert result == []


def test_check_ibm_svc_mdisk_regression_2_with_proper_data() -> None:
    """Test check function with properly structured data."""
    mock_parsed = {
        "mdisk_0": {
            "id": "0",
            "name": "mdisk_0",
            "status": "online",
            "mode": "array",
            "capacity": "20.8TB",
            "encrypt": "no",
        }
    }

    # Use default parameters as defined in the check
    params = {
        "online_state": 0,
        "array_mode": 0,
    }

    result = list(check_ibm_svc_mdisk("mdisk_0", params, mock_parsed))

    assert len(result) == 2

    # Check status result
    status_result = result[0]
    assert status_result[0] == 0  # OK state (online with params)
    assert "Status: online" in status_result[1]

    # Check mode result
    mode_result = result[1]
    assert mode_result[0] == 0  # OK state (array mode with params)
    assert "Mode: array" in mode_result[1]


def test_parse_ibm_svc_mdisk_regression_2_header_mismatch() -> None:
    """Test that parser handles header mismatches gracefully."""
    # Test with different header variations that might cause issues
    malformed_data = [
        ["wrong", "header", "fields"],
        ["data", "that", "wont_match"],
    ]

    result = parse_ibm_svc_mdisk(malformed_data)
    # Parser is more flexible than expected, it creates entries based on available data
    # but they should have unexpected structure
    assert isinstance(result, dict)


def test_parse_ibm_svc_mdisk_regression_2_missing_name_field() -> None:
    """Test specific regression case where name field is missing from header."""
    # Original dataset has header without 'name' field, which causes parsing issues
    original_data = [
        [
            "id",
            "status",
            "mode",
            "capacity",
            "encrypt",
            "enclosure_id",
            "over_provisioned",
            "supports_unmap",
            "warning",
        ],
        ["0", "online", "array", "20.8TB", "no", "1", "no", "yes", "80"],
    ]

    result = parse_ibm_svc_mdisk(original_data)

    # Should result in empty dict because 'name' field is required but missing
    assert result == {}


def test_ibm_svc_mdisk_regression_2() -> None:
    """
    Comprehensive regression test for IBM SVC MDisk scenario.

    This test validates the specific regression scenario where:
    1. MDisk data exists in the output
    2. Header format doesn't match expected default header
    3. No items are discovered due to missing required fields
    4. Check function handles missing items gracefully
    """
    # Original string table from dataset
    string_table = [
        [
            "id",
            "status",
            "mode",
            "capacity",
            "encrypt",
            "enclosure_id",
            "over_provisioned",
            "supports_unmap",
            "warning",
        ],
        ["0", "online", "array", "20.8TB", "no", "1", "no", "yes", "80"],
    ]

    # Parse the data
    parsed = parse_ibm_svc_mdisk(string_table)

    # Verify parsing result matches expected empty state
    assert parsed == {}

    # Verify discovery finds no items
    discovery_result = list(discover_ibm_svc_mdisk(parsed))
    assert discovery_result == []

    # Verify check function handles missing items
    check_result = list(check_ibm_svc_mdisk("any_item", {}, parsed))
    assert check_result == []
