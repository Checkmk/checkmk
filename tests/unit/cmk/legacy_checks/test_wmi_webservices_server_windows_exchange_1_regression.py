#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.legacy_checks import wmi_webservices
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
    result = list(wmi_webservices.discover_wmi_webservices(parsed))

    # Should discover both web sites
    assert len(result) == 2
    expected_services = {"Default Web Site", "Exchange Back End"}
    discovered_services = {service.item for service in result}
    assert discovered_services == expected_services


def test_wmi_webservices_check_default_site(parsed: Mapping[str, Any]) -> None:
    """Test WMI Web Services check function for Default Web Site."""
    # Based on the original dataset, Default Web Site has 0 connections
    result = list(wmi_webservices.check_wmi_webservices("Default Web Site", parsed))

    assert result == [
        Result(state=State.OK, summary="Connections: 0"),
        Metric("connections", 0),
    ]


def test_wmi_webservices_check_exchange_backend(parsed: Mapping[str, Any]) -> None:
    """Test WMI Web Services check function for Exchange Back End."""
    # Based on the original dataset, Exchange Back End has 11 connections
    result = list(wmi_webservices.check_wmi_webservices("Exchange Back End", parsed))

    assert result == [
        Result(state=State.OK, summary="Connections: 11"),
        Metric("connections", 11),
    ]


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
    result = list(wmi_webservices.discover_wmi_webservices(parsed))

    assert result == []
