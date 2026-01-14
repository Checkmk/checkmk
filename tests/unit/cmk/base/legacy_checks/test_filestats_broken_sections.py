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

from cmk.base.legacy_checks.filestats import (
    check_filestats,
    discover_filestats,
    parse_filestats,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for filestats with broken/malformed sections"""
    return [
        ["some garbage in the first line (should be ignored)"],
        ["[[[count_only ok subsection]]]"],
        ["{'type': 'summary', 'count': 23}"],
        ["[[[count_only missing count]]]"],
        ["{'type': 'summary', 'foobar': 42}"],
        ["[[[count_only complete mess]]]"],
        ["{'fooba2adrs: gh"],
        ["[[[count_only empty subsection]]]"],
        ["{}"],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> dict[str, Any]:
    """Parsed filestats data with broken sections"""
    return parse_filestats(string_table)


def test_discover_filestats(parsed: dict[str, Any]) -> None:
    """Test filestats discovery finds all valid subsections"""
    discovered = list(discover_filestats(parsed))
    assert len(discovered) == 4

    # Should discover all subsections
    subsection_names = [item[0] for item in discovered]
    assert "ok subsection" in subsection_names
    assert "missing count" in subsection_names
    assert "complete mess" in subsection_names
    assert "empty subsection" in subsection_names

    # All should have empty parameters
    for _, params in discovered:
        assert params == {}


def test_check_filestats_ok_subsection(parsed: dict[str, Any]) -> None:
    """Test filestats check for working subsection with count"""
    result = list(check_filestats("ok subsection", {}, parsed))
    assert len(result) == 1

    state, message, metrics = result[0]
    assert state == 0  # OK
    assert message == "Files in total: 23"
    assert len(metrics) == 1
    assert metrics[0] == ("file_count", 23, None, None)


def test_check_filestats_missing_count(parsed: dict[str, Any]) -> None:
    """Test filestats check for subsection missing count field"""
    result = list(check_filestats("missing count", {}, parsed))
    # Should return empty generator (no results) when count is missing
    assert len(result) == 0


def test_check_filestats_complete_mess(parsed: dict[str, Any]) -> None:
    """Test filestats check for subsection with malformed JSON"""
    result = list(check_filestats("complete mess", {}, parsed))
    # Should return empty generator when parsing fails completely
    assert len(result) == 0


def test_check_filestats_empty_subsection(parsed: dict[str, Any]) -> None:
    """Test filestats check for subsection with empty data"""
    result = list(check_filestats("empty subsection", {}, parsed))
    # Should return empty generator when no summary data available
    assert len(result) == 0


def test_check_filestats_nonexistent_item(parsed: dict[str, Any]) -> None:
    """Test filestats check for non-existent subsection"""
    result = list(check_filestats("nonexistent", {}, parsed))
    assert len(result) == 0


def test_parse_filestats_structure(string_table: list[list[str]]) -> None:
    """Test filestats parsing creates correct data structure"""
    parsed = parse_filestats(string_table)

    # Should have 4 subsections (empty lines and garbage ignored)
    assert len(parsed) == 4
    assert "ok subsection" in parsed
    assert "missing count" in parsed
    assert "complete mess" in parsed
    assert "empty subsection" in parsed

    # Check structure for working subsection
    variety, data = parsed["ok subsection"]
    assert variety == "count_only"
    assert len(data) == 1
    assert data[0] == {"type": "summary", "count": 23}

    # Check structure for missing count subsection
    variety, data = parsed["missing count"]
    assert variety == "count_only"
    assert len(data) == 1
    assert data[0] == {"type": "summary", "foobar": 42}

    # Check structure for malformed subsection (should be empty due to SyntaxError)
    variety, data = parsed["complete mess"]
    assert variety == "count_only"
    assert len(data) == 0  # Malformed JSON filtered out

    # Check structure for empty subsection
    variety, data = parsed["empty subsection"]
    assert variety == "count_only"
    assert len(data) == 1
    assert data[0] == {}


def test_check_filestats_with_parameters() -> None:
    """Test filestats check with warning/critical thresholds"""
    # Create simple working data
    test_data = [
        ["[[[count_only test files]]]"],
        ["{'type': 'summary', 'count': 150}"],
    ]

    parsed = parse_filestats(test_data)

    # Test with count thresholds
    params = {
        "mincount": (100, 50),  # warn below 100, crit below 50
        "maxcount": (200, 300),  # warn above 200, crit above 300
    }

    result = list(check_filestats("test files", params, parsed))
    assert len(result) == 1

    state, message, metrics = result[0]
    assert state == 0  # Should be OK (150 is within 100-200 range)
    assert "Files in total: 150" in message
    assert ("file_count", 150, 200, 300) in metrics


def test_filestats_parsing_error_handling() -> None:
    """Test that parsing handles various JSON syntax errors gracefully"""
    malformed_data = [
        ["[[[test malformed json]]]"],
        ["{'type': 'summary', 'count': 42}"],  # Valid
        ["{'incomplete': "],  # Invalid - missing closing
        ["not json at all"],  # Invalid - not JSON
        ["{'valid': 'again', 'count': 5}"],  # Valid
        ["{"],  # Invalid - incomplete
    ]

    parsed = parse_filestats(malformed_data)
    variety, data = parsed["malformed json"]

    # Should only have the 2 valid JSON objects
    assert len(data) == 2
    assert data[0] == {"type": "summary", "count": 42}
    assert data[1] == {"valid": "again", "count": 5}
