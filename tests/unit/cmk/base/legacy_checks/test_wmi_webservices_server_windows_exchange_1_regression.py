#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.wmi_webservices import check_wmi_webservices, discover_wmi_webservices
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table


@pytest.fixture(name="parsed")
def fixture_parsed() -> Mapping[str, Any]:
    """Parsed WMI data fixture for WMI Web Services."""
    string_table = [
        [
            "AnonymousUsersPersec",
            "BytesReceivedPersec",
            "CurrentConnections",
            "Frequency_Object",
            "Frequency_PerfTime",
            "Frequency_Sys100NS",
            "Timestamp_Object",
            "Timestamp_PerfTime",
            "Timestamp_Sys100NS",
            "Name",
        ],
        [
            "0",
            "0",
            "0",
            "1953125",
            "10000000",
            "0",
            "1953125",
            "10000000",
            "0",
            "Default Web Site",
        ],
        [
            "0",
            "0",
            "11",
            "1953125",
            "10000000",
            "0",
            "1953125",
            "10000000",
            "0",
            "Exchange Back End",
        ],
    ]
    return parse_wmi_table(string_table)


def test_wmi_webservices_discovery(parsed: Mapping[str, Any]) -> None:
    """Test discovery function returns correct items."""
    result = list(discover_wmi_webservices(parsed))

    # Should discover both web sites
    assert len(result) == 2
    expected_services = {"Default Web Site", "Exchange Back End"}
    discovered_services = {item for item, _ in result}
    assert discovered_services == expected_services


@pytest.mark.usefixtures("initialised_item_state")
def test_wmi_webservices_check_default_site(parsed: Mapping[str, Any]) -> None:
    """Test WMI Web Services check function for Default Web Site."""
    # Based on the original dataset, Default Web Site has 0 connections
    result = list(check_wmi_webservices("Default Web Site", {}, parsed))

    # Should have 1 result for connections
    assert len(result) == 1

    # Check the connection count result
    assert result[0][0] == 0  # OK state
    assert "Connections: 0" in result[0][1]
    assert result[0][2][0][0] == "connections"
    assert result[0][2][0][1] == 0


@pytest.mark.usefixtures("initialised_item_state")
def test_wmi_webservices_check_exchange_backend(parsed: Mapping[str, Any]) -> None:
    """Test WMI Web Services check function for Exchange Back End."""
    # Based on the original dataset, Exchange Back End has 11 connections
    result = list(check_wmi_webservices("Exchange Back End", {}, parsed))

    # Should have 1 result for connections
    assert len(result) == 1

    # Check the connection count result
    assert result[0][0] == 0  # OK state
    assert "Connections: 11" in result[0][1]
    assert result[0][2][0][0] == "connections"
    assert result[0][2][0][1] == 11


def test_wmi_webservices_parse_function() -> None:
    """Test WMI Web Services parse function with minimal dataset."""
    string_table = [
        [
            "CurrentConnections",
            "Frequency_Object",
            "Frequency_PerfTime",
            "Timestamp_Object",
            "Timestamp_PerfTime",
            "Name",
        ],
        [
            "0",
            "1953125",
            "10000000",
            "1953125",
            "10000000",
            "Default Web Site",
        ],
        [
            "11",
            "1953125",
            "10000000",
            "1953125",
            "10000000",
            "Exchange Back End",
        ],
    ]

    parsed = parse_wmi_table(string_table)

    assert "" in parsed
    # Access WMITable with row parameter (indexed by row number)
    wmi_table = parsed[""]

    # Check first row (Default Web Site)
    assert wmi_table.get("Default Web Site", "CurrentConnections") == "0"
    assert wmi_table.get("Default Web Site", "Name") == "Default Web Site"

    # Check second row (Exchange Back End)
    assert wmi_table.get("Exchange Back End", "CurrentConnections") == "11"
    assert wmi_table.get("Exchange Back End", "Name") == "Exchange Back End"


def test_wmi_webservices_discovery_empty_section() -> None:
    """Test discovery with empty data."""
    string_table: list[list[str]] = []

    parsed = parse_wmi_table(string_table)
    result = list(discover_wmi_webservices(parsed))

    assert result == []
