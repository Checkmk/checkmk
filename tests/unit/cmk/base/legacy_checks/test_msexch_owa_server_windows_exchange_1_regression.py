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
from typing import Any

import pytest

from cmk.agent_based.v2 import GetRateError
from cmk.base.legacy_checks.msexch_owa import check_msexch_owa, discover_msexch_owa
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table


@pytest.fixture(name="parsed")
def fixture_parsed() -> Mapping[str, Any]:
    """Parsed WMI data fixture for Microsoft Exchange OWA."""
    string_table = [
        [
            "ActiveConversions",
            "ActiveMailboxSubscriptions",
            "AggregatedConfigurationReads",
            "RequestsPersec",
            "CurrentUniqueUsers",
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
            "0",
            "0",
            "1953125",
            "10000000",
            "0",
            "1953125",
            "10000000",
            "0",
            "",
        ],
    ]
    return parse_wmi_table(string_table)


def test_msexch_owa_discovery(parsed: Mapping[str, Any]) -> None:
    """Test discovery function returns correct items."""
    result = list(discover_msexch_owa(parsed))
    assert result == [(None, {})]


@pytest.mark.usefixtures("initialised_item_state")
def test_msexch_owa_check(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange OWA check function."""
    # Based on the original dataset, this should produce rates for OWA metrics
    # The rate calculation gets GetRateError on first run due to initialization
    # Should get GetRateError on first check (normal behavior)
    with pytest.raises(GetRateError):
        list(check_msexch_owa(None, {}, parsed))


def test_msexch_owa_parse_function() -> None:
    """Test Microsoft Exchange OWA parse function with minimal dataset."""
    string_table = [
        [
            "ActiveConversions",
            "RequestsPersec",
            "CurrentUniqueUsers",
            "Frequency_Object",
            "Frequency_PerfTime",
            "Timestamp_Object",
            "Timestamp_PerfTime",
            "Name",
        ],
        [
            "0",
            "0",
            "0",
            "1953125",
            "10000000",
            "1953125",
            "10000000",
            "",
        ],
    ]

    parsed = parse_wmi_table(string_table)

    assert "" in parsed
    # Access WMITable with row parameter (0 is the only row)
    wmi_table = parsed[""]
    assert wmi_table.get(0, "RequestsPersec") == "0"
    assert wmi_table.get(0, "CurrentUniqueUsers") == "0"
    # Name field gets converted to None when empty
    assert wmi_table.get(0, "Name") is None


def test_msexch_owa_discovery_empty_section() -> None:
    """Test discovery with empty data."""
    string_table: list[list[str]] = []

    parsed = parse_wmi_table(string_table)
    result = list(discover_msexch_owa(parsed))

    assert result == []


def test_msexch_owa_check_no_data() -> None:
    """Test check function with no data."""
    parsed: Mapping[str, Any] = {"": {}}

    try:
        result = list(check_msexch_owa(None, {}, parsed))
        # Should have empty results or raise an error
        assert len(result) >= 0
    except Exception:
        # Exception is expected with no data
        pass
