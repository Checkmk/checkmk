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

from cmk.agent_based.v2 import GetRateError
from cmk.base.legacy_checks.msexch_autodiscovery import (
    check_msexch_autodiscovery,
    discover_msexch_autodiscovery,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table


@pytest.fixture
def parsed() -> Mapping[str, Any]:
    """Create parsed Microsoft Exchange Autodiscovery data using actual parse function."""
    string_table = [
        [
            "Caption",
            "Description",
            "ErrorResponses",
            "ErrorResponsesPersec",
            "Frequency_Object",
            "Frequency_PerfTime",
            "Frequency_Sys100NS",
            "Name",
            "ProcessID",
            "RequestsPersec",
            "Timestamp_Object",
            "Timestamp_PerfTime",
            "Timestamp_Sys100NS",
            "TotalRequests",
        ],
        [
            "",  # Caption
            "",  # Description
            "0",  # ErrorResponses
            "0",  # ErrorResponsesPersec
            "0",  # Frequency_Object
            "2343747",  # Frequency_PerfTime
            "10000000",  # Frequency_Sys100NS
            "",  # Name - empty for _Total instance
            "29992",  # ProcessID
            "19086",  # RequestsPersec - key metric
            "0",  # Timestamp_Object
            "1025586529184",  # Timestamp_PerfTime
            "131287884132350000",  # Timestamp_Sys100NS
            "19086",  # TotalRequests
        ],
    ]

    return parse_wmi_table(string_table)


def test_msexch_autodiscovery_discovery(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange Autodiscovery discovery function."""
    result = list(discover_msexch_autodiscovery(parsed))

    # Should discover exactly one service (empty string as item name)
    assert len(result) == 1
    assert result[0] == (None, {})


@pytest.mark.usefixtures("initialised_item_state")
def test_msexch_autodiscovery_check(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange Autodiscovery check function."""
    # Based on the original dataset, this should produce a rate of 0.00 requests/sec
    # The rate calculation gets GetRateError on first run due to initialization
    # Should get GetRateError on first check (normal behavior)
    with pytest.raises(GetRateError):
        list(check_msexch_autodiscovery(None, {}, parsed))


def test_msexch_autodiscovery_parse_function() -> None:
    """Test Microsoft Exchange Autodiscovery parse function with minimal dataset."""
    string_table = [
        [
            "RequestsPersec",
            "TotalRequests",
            "Frequency_PerfTime",
            "Name",
        ],
        [
            "19086",
            "19086",
            "2343747",
            "",
        ],
    ]

    result = parse_wmi_table(string_table)

    # Should parse exactly one WMI instance
    assert "" in result
    wmi_data = result[""]

    # Check that it's a WMI table object (not the internal structure)
    assert hasattr(wmi_data, "__class__")
    assert "WMITable" in wmi_data.__class__.__name__


def test_msexch_autodiscovery_discovery_empty_section() -> None:
    """Test Microsoft Exchange Autodiscovery discovery function with empty section."""
    result = list(discover_msexch_autodiscovery({}))

    # Should not discover any service for empty section
    assert len(result) == 0


def test_msexch_autodiscovery_check_no_data() -> None:
    """Test Microsoft Exchange Autodiscovery check function with no data."""
    # Check function expects key "" to exist, so it will raise KeyError on missing data
    with pytest.raises(KeyError):
        list(check_msexch_autodiscovery(None, {}, {}))
