#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="redundant-expr"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

from cmk.base.legacy_checks.raritan_px_outlets import (
    check_raritan_px_outlets,
    discover_raritan_px_outlets,
    parse_raritan_px_outlets,
)


def parsed() -> dict[str, Any]:
    """Parse raritan_px_outlets test data using actual parse function."""
    string_table = [
        [
            "3",
            "label",
            "1",
            "3",
            "3",
            "3",
            "3",
            "3",
        ],
        [
            "2",
            "",
            "1",
            "3",
            "3",
            "3",
            "3",
            "3",
        ],
    ]

    return parse_raritan_px_outlets(string_table)


def test_raritan_px_outlets_discovery() -> None:
    """Test discovery of raritan_px_outlets items."""
    discovery_result = list(discover_raritan_px_outlets(parsed()))

    # Sort for comparison since order may vary
    assert sorted(discovery_result) == sorted([("3", {}), ("2", {})])


def test_raritan_px_outlets_check_with_label() -> None:
    """Test check function for outlet with label."""
    results = list(check_raritan_px_outlets("3", {}, parsed()))

    # Should have multiple results from elphase check
    assert len(results) >= 2

    # First result should be the label
    first_result = results[0]
    if len(first_result) == 2:
        state, summary = first_result
    elif len(first_result) == 3:
        state, summary, metrics = first_result
    else:
        assert False, f"Unexpected result format: {first_result}"

    assert state == 0  # OK
    assert "[label]" in summary

    # Additional results come from check_elphase function
    # Check that device status is included
    has_device_status = any("Device status" in result[1] for result in results if len(result) >= 2)
    assert has_device_status


def test_raritan_px_outlets_check_without_label() -> None:
    """Test check function for outlet without label."""
    results = list(check_raritan_px_outlets("2", {}, parsed()))

    # Should have multiple results from elphase check
    assert len(results) >= 1

    # Should not have label result since label is empty
    for result in results:
        # Handle both 2-tuple and 3-tuple return formats
        if len(result) == 2:
            state, summary = result
        elif len(result) == 3:
            state, summary, metrics = result
        else:
            assert False, f"Unexpected result format: {result}"

        assert "[" not in summary or "Device status" in summary


def test_raritan_px_outlets_check_missing_item() -> None:
    """Test check function for missing outlet item."""
    results = list(check_raritan_px_outlets("999", {}, parsed()))

    # Should return no results for missing item
    assert results == []


def test_raritan_px_outlets_parse_scaling() -> None:
    """Test that parsing correctly scales values."""
    test_data = parsed()

    # Verify scaling is applied correctly
    outlet_3 = test_data["3"]
    assert outlet_3["current"] == 0.003  # 3 / 1000
    assert outlet_3["voltage"] == 0.003  # 3 / 1000
    assert outlet_3["power"] == 3.0  # No scaling
    assert outlet_3["appower"] == 3.0  # No scaling
    assert outlet_3["energy"] == 3.0  # No scaling
    assert outlet_3["device_state"] == (0, "on")  # State 1 maps to "on"
    assert outlet_3["label"] == "label"
