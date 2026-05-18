#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import GetRateError, Service
from cmk.legacy_checks import msexch_autodiscovery
from cmk.plugins.windows.agent_based import libwmi as wmi
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, object] = {}
    monkeypatch.setattr(wmi, "get_value_store", lambda: store)


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
    result = list(msexch_autodiscovery.discover_msexch_autodiscovery(parsed))
    assert result == [Service(item=None)]


@pytest.mark.usefixtures("empty_value_store")
def test_msexch_autodiscovery_check(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange Autodiscovery check function."""
    # The rate calculation gets GetRateError on first run due to initialization
    with pytest.raises(GetRateError):
        list(msexch_autodiscovery.check_msexch_autodiscovery(parsed))


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
    result = list(msexch_autodiscovery.discover_msexch_autodiscovery({}))

    # Should not discover any service for empty section
    assert len(result) == 0


def test_msexch_autodiscovery_check_no_data() -> None:
    """Test Microsoft Exchange Autodiscovery check function with no data."""
    # Check function expects key "" to exist, so it will raise KeyError on missing data
    with pytest.raises(KeyError):
        list(msexch_autodiscovery.check_msexch_autodiscovery({}))
