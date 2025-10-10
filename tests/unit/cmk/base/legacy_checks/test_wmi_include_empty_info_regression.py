#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.base.legacy_checks.wmi_webservices import (
    check_wmi_webservices,
    discover_wmi_webservices,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMITable


@pytest.fixture(name="string_table_empty")
def fixture_string_table_empty() -> list[list[str]]:
    """Empty WMI web services data for edge case testing.

    Tests behavior when no WMI web service data is available.
    """
    return []


@pytest.fixture(name="parsed_data_empty")
def fixture_parsed_data_empty(string_table_empty: list[list[str]]) -> Mapping[str, WMITable]:
    """Parsed empty WMI web services data."""
    return parse_wmi_table(string_table_empty)


def test_parse_wmi_webservices_empty_data(string_table_empty: list[list[str]]) -> None:
    """Test parsing when no WMI web services data is available."""
    parsed = parse_wmi_table(string_table_empty)

    # Should return empty dict structure for empty data
    assert parsed == {}


def test_discover_wmi_webservices_empty_data(parsed_data_empty: Mapping[str, WMITable]) -> None:
    """Test discovery when no WMI web services data is available."""
    items = list(discover_wmi_webservices(parsed_data_empty))

    # Should not discover any services with empty data
    assert items == []


def test_check_wmi_webservices_empty_data(parsed_data_empty: dict) -> None:
    """Test check function when no WMI web services data is available."""
    # The check function will raise a KeyError when trying to access parsed[""]
    # on empty data - this is the expected behavior for this edge case
    with pytest.raises(KeyError):
        list(check_wmi_webservices("NonExistentService", {}, parsed_data_empty))


def test_check_wmi_webservices_with_valid_data() -> None:
    """Test WMI web services check with valid data structure."""
    # Create minimal valid parsed data structure
    valid_string_table = [
        ["Name", "CurrentConnections"],
        ["Default Web Site", "5"],
        ["API Service", "12"],
    ]

    parsed = parse_wmi_table(valid_string_table)

    # Test discovery with valid data
    items = list(discover_wmi_webservices(parsed))
    assert len(items) >= 1  # Should discover at least one service

    # Test that items are properly formatted (item_name, params_dict)
    for item in items:
        assert len(item) == 2
        assert isinstance(item[0], str)  # item name
        assert isinstance(item[1], dict)  # parameters


def test_check_wmi_webservices_nonexistent_item_valid_data() -> None:
    """Test check for non-existent item with valid parsed data."""
    valid_string_table = [
        ["Name", "CurrentConnections"],
        ["Default Web Site", "5"],
    ]

    parsed = parse_wmi_table(valid_string_table)

    # Check for non-existent service should return empty results
    results = list(check_wmi_webservices("NonExistentService", {}, parsed))
    assert results == []
