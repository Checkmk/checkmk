#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""
Test regression scenarios for .NET CLR Memory monitoring with Kaspersky error case.
This test covers the dotnet_clrmemory check with WMI data showing low GC time (0.07%)
from a Windows server with various .NET processes including Kaspersky-related services.
"""

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.dotnet_clrmemory import (
    check_dotnet_clrmemory,
    discover_dotnet_clrmemory,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection


@pytest.fixture(name="test_data")
def fixture_test_data() -> list[list[str]]:
    """WMI data for .NET CLR Memory with Kaspersky error regression test."""
    return [
        [
            "AllocatedBytesPersec",
            "Caption",
            "Description",
            "FinalizationSurvivors",
            "Frequency_Object",
            "Frequency_PerfTime",
            "Frequency_Sys100NS",
            "Gen0heapsize",
            "Gen0PromotedBytesPerSec",
            "Gen1heapsize",
            "Gen1PromotedBytesPerSec",
            "Gen2heapsize",
            "LargeObjectHeapsize",
            "Name",
            "NumberBytesinallHeaps",
            "NumberGCHandles",
            "NumberGen0Collections",
            "NumberGen1Collections",
            "NumberGen2Collections",
            "NumberInducedGC",
            "NumberofPinnedObjects",
            "NumberofSinkBlocksinuse",
            "NumberTotalcommittedBytes",
            "NumberTotalreservedBytes",
            "PercentTimeinGC",
            "PercentTimeinGC_Base",
            "ProcessID",
            "PromotedFinalizationMemoryfromGen0",
            "PromotedMemoryfromGen0",
            "PromotedMemoryfromGen1",
            "Timestamp_Object",
            "Timestamp_PerfTime",
            "Timestamp_Sys100NS",
        ],
        [
            "46584024",
            "",
            "",
            "201",
            "0",
            "3914064",
            "10000000",
            "6291456",
            "1110904",
            "1100372",
            "850168",
            "3279916",
            "73912",
            "_Global_",
            "4454200",
            "1470",
            "4",
            "3",
            "1",
            "0",
            "39",
            "135",
            "10493952",
            "33546240",
            "3003926",
            "-1",
            "0",
            "15076",
            "1110904",
            "850168",
            "0",
            "9918361461",
            "131261124692120000",
        ],
        [
            "0",
            "",
            "",
            "0",
            "0",
            "3914064",
            "10000000",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "isa",
            "0",
            "41",
            "0",
            "0",
            "0",
            "0",
            "0",
            "8",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "9918361461",
            "131261124692120000",
        ],
        [
            "0",
            "",
            "",
            "0",
            "0",
            "3914064",
            "10000000",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "SCNotification",
            "0",
            "390",
            "0",
            "0",
            "0",
            "0",
            "0",
            "65",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "9918361461",
            "131261124692120000",
        ],
        [
            "23292012",
            "",
            "",
            "201",
            "0",
            "3914064",
            "10000000",
            "6291456",
            "1110904",
            "1100372",
            "850168",
            "3279916",
            "73912",
            "IAStorDataMgrSvc",
            "4454200",
            "678",
            "4",
            "3",
            "1",
            "0",
            "39",
            "30",
            "10493952",
            "33546240",
            "162041",
            "46336747",
            "5804",
            "15076",
            "1110904",
            "850168",
            "0",
            "9918361461",
            "131261124692120000",
        ],
        [
            "0",
            "",
            "",
            "0",
            "0",
            "3914064",
            "10000000",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "CcmExec",
            "0",
            "21",
            "0",
            "0",
            "0",
            "0",
            "0",
            "2",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "9918361461",
            "131261124692120000",
        ],
        [
            "0",
            "",
            "",
            "0",
            "0",
            "3914064",
            "10000000",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "IAStorIcon",
            "0",
            "340",
            "0",
            "0",
            "0",
            "0",
            "0",
            "30",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "9918361461",
            "131261124692120000",
        ],
    ]


@pytest.fixture(name="parsed_wmi")
def fixture_parsed_wmi(test_data: list[list[str]]) -> WMISection:
    """Parse WMI data using actual WMI parser and return section dict."""
    return parse_wmi_table(test_data)


def test_discover_dotnet_clrmemory(parsed_wmi: WMISection) -> None:
    """Test discovery finds _Global_ instance with default levels."""
    discoveries = list(discover_dotnet_clrmemory(parsed_wmi))
    assert discoveries == [Service(item="_Global_")]


def test_check_dotnet_clrmemory_global_instance(parsed_wmi: WMISection) -> None:
    """Test check function for _Global_ instance with low GC time (0.07%)."""
    results = list(check_dotnet_clrmemory("_Global_", {"upper": (10.0, 15.0)}, parsed_wmi))

    assert len(results) == 2
    result_obj, metric = results
    assert isinstance(result_obj, Result)
    assert isinstance(metric, Metric)

    assert result_obj.state == State.OK
    assert "Time spent in Garbage Collection: 0.07%" in result_obj.summary

    assert metric.name == "percent"
    assert abs(metric.value - 0.06994060242314372) < 0.0001
    assert metric.levels == (10.0, 15.0)
    assert metric.boundaries == (0.0, 100.0)


def test_check_dotnet_clrmemory_nonexistent_item(parsed_wmi: WMISection) -> None:
    """Test check function with nonexistent item returns no results."""
    results = list(check_dotnet_clrmemory("NonExistent", {"upper": (10.0, 15.0)}, parsed_wmi))
    assert results == []


def test_check_dotnet_clrmemory_warning_threshold(parsed_wmi: WMISection) -> None:
    """Test check function with lowered warning threshold triggers warning state."""
    params = {"upper": (0.05, 15.0)}
    results = list(check_dotnet_clrmemory("_Global_", params, parsed_wmi))

    assert len(results) == 2
    result_obj, _metric = results
    assert isinstance(result_obj, Result)

    assert result_obj.state == State.WARN
    assert "Time spent in Garbage Collection: 0.07%" in result_obj.summary


def test_check_dotnet_clrmemory_critical_threshold(parsed_wmi: WMISection) -> None:
    """Test check function with very low critical threshold triggers critical state."""
    params = {"upper": (0.01, 0.05)}
    results = list(check_dotnet_clrmemory("_Global_", params, parsed_wmi))

    assert len(results) == 2
    result_obj, _metric = results
    assert isinstance(result_obj, Result)

    assert result_obj.state == State.CRIT
    assert "Time spent in Garbage Collection: 0.07%" in result_obj.summary


def test_dotnet_clrmemory_server_windows_kaspersky_error_regression(
    parsed_wmi: WMISection,
) -> None:
    """Test main regression scenario with original expected values."""
    results = list(check_dotnet_clrmemory("_Global_", {"upper": (10.0, 15.0)}, parsed_wmi))

    assert len(results) == 2
    result_obj, metric = results
    assert isinstance(result_obj, Result)
    assert isinstance(metric, Metric)

    assert result_obj.state == State.OK
    assert result_obj.summary == "Time spent in Garbage Collection: 0.07%"

    assert metric.name == "percent"
    assert abs(metric.value - 0.06994060242314372) < 0.0001
    assert metric.levels == (10.0, 15.0)
    assert metric.boundaries == (0.0, 100.0)
