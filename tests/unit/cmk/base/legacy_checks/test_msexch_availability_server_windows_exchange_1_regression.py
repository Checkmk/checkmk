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
from cmk.base.legacy_checks.msexch_availability import (
    check_msexch_availability,
    discover_msexch_availability,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table


@pytest.fixture
def parsed() -> Mapping[str, Any]:
    """Create parsed Microsoft Exchange Availability data using actual parse function."""
    string_table = [
        [
            "AvailabilityRequestssec",
            "AverageNumberofMailboxesProcessedperRequest",
            "AverageNumberofMailboxesProcessedperRequest_Base",
            "AverageTimetoMapExternalCallertoInternalIdentity",
            "AverageTimetoMapExternalCallertoInternalIdentity_Base",
            "AverageTimetoProcessaCrossForestFreeBusyRequest",
            "AverageTimetoProcessaCrossForestFreeBusyRequest_Base",
            "AverageTimetoProcessaCrossSiteFreeBusyRequest",
            "AverageTimetoProcessaCrossSiteFreeBusyRequest_Base",
            "AverageTimetoProcessaFederatedFreeBusyRequest",
            "AverageTimetoProcessaFederatedFreeBusyRequest_Base",
            "AverageTimetoProcessaFederatedFreeBusyRequestwithOAuth",
            "AverageTimetoProcessaFederatedFreeBusyRequestwithOAuth_Base",
            "AverageTimetoProcessaFreeBusyRequest",
            "AverageTimetoProcessaFreeBusyRequest_Base",
            "AverageTimetoProcessanIntraSiteFreeBusyRequest",
            "AverageTimetoProcessanIntraSiteFreeBusyRequest_Base",
            "Caption",
            "ClientReportedFailures",
            "CrossForestCalendarFailures",
            "CrossForestCalendarQueries",
            "CrossSiteCalendarFailures",
            "CrossSiteCalendarQueries",
            "Description",
            "FederatedByOAuthCalendarFailures",
            "FederatedByOAuthCalendarQueries",
            "FederatedFreeBusyQueries",
            "FederatedFreebusyFailures",
            "Frequency_Object",
            "Frequency_PerfTime",
            "Frequency_Sys100NS",
            "IntraSiteCalendarFailures",
            "IntraSiteCalendarQueries",
            "Name",
            "PublicFolderQueries",
            "PublicFolderQueriesFailures",
            "SuggestionsRequestssec",
            "Timestamp_Object",
            "Timestamp_PerfTime",
            "Timestamp_Sys100NS",
        ],
        [
            "0",  # AvailabilityRequestssec - key metric
            "0",  # AverageNumberofMailboxesProcessedperRequest
            "0",  # AverageNumberofMailboxesProcessedperRequest_Base
            "0",  # AverageTimetoMapExternalCallertoInternalIdentity
            "0",  # AverageTimetoMapExternalCallertoInternalIdentity_Base
            "0",  # AverageTimetoProcessaCrossForestFreeBusyRequest
            "0",  # AverageTimetoProcessaCrossForestFreeBusyRequest_Base
            "0",  # AverageTimetoProcessaCrossSiteFreeBusyRequest
            "0",  # AverageTimetoProcessaCrossSiteFreeBusyRequest_Base
            "0",  # AverageTimetoProcessaFederatedFreeBusyRequest
            "0",  # AverageTimetoProcessaFederatedFreeBusyRequest_Base
            "0",  # AverageTimetoProcessaFederatedFreeBusyRequestwithOAuth
            "0",  # AverageTimetoProcessaFederatedFreeBusyRequestwithOAuth_Base
            "0",  # AverageTimetoProcessaFreeBusyRequest
            "0",  # AverageTimetoProcessaFreeBusyRequest_Base
            "0",  # AverageTimetoProcessanIntraSiteFreeBusyRequest
            "0",  # AverageTimetoProcessanIntraSiteFreeBusyRequest_Base
            "",  # Caption
            "0",  # ClientReportedFailures
            "0",  # CrossForestCalendarFailures
            "0",  # CrossForestCalendarQueries
            "0",  # CrossSiteCalendarFailures
            "0",  # CrossSiteCalendarQueries
            "",  # Description
            "0",  # FederatedByOAuthCalendarFailures
            "0",  # FederatedByOAuthCalendarQueries
            "0",  # FederatedFreeBusyQueries
            "0",  # FederatedFreebusyFailures
            "0",  # Frequency_Object
            "13604",  # Frequency_PerfTime
            "10000000",  # Frequency_Sys100NS
            "0",  # IntraSiteCalendarFailures
            "0",  # IntraSiteCalendarQueries
            "",  # Name - empty for _Total instance
            "0",  # PublicFolderQueries
            "0",  # PublicFolderQueriesFailures
            "0",  # SuggestionsRequestssec
            "6743176212200",  # Timestamp_Object
            "130951777565030000",  # Timestamp_PerfTime
            "0",  # Timestamp_Sys100NS
        ],
    ]

    return parse_wmi_table(string_table)


def test_msexch_availability_discovery(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange Availability discovery function."""
    result = list(discover_msexch_availability(parsed))

    # Should discover exactly one service (empty string as item name)
    assert len(result) == 1
    assert result[0] == (None, {})


@pytest.mark.usefixtures("initialised_item_state")
def test_msexch_availability_check(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange Availability check function."""
    # Based on the original dataset, this should produce a rate of 0.00 requests/sec
    # The rate calculation gets GetRateError on first run due to initialization
    # Should get GetRateError on first check (normal behavior)
    with pytest.raises(GetRateError):
        list(check_msexch_availability(None, {}, parsed))


def test_msexch_availability_parse_function() -> None:
    """Test Microsoft Exchange Availability parse function with minimal dataset."""
    string_table = [
        [
            "AvailabilityRequestssec",
            "SuggestionsRequestssec",
            "Frequency_PerfTime",
            "Name",
        ],
        [
            "0",
            "0",
            "13604",
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


def test_msexch_availability_discovery_empty_section() -> None:
    """Test Microsoft Exchange Availability discovery function with empty section."""
    result = list(discover_msexch_availability({}))

    # Should not discover any service for empty section
    assert len(result) == 0


def test_msexch_availability_check_no_data() -> None:
    """Test Microsoft Exchange Availability check function with no data."""
    # Check function expects key "" to exist, so it will raise KeyError on missing data
    with pytest.raises(KeyError):
        list(check_msexch_availability(None, {}, {}))
