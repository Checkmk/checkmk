#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.dotnet_clrmemory import (
    check_dotnet_clrmemory,
    discover_dotnet_clrmemory,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection


@pytest.fixture(name="string_table")
def string_table_fixture() -> StringTable:
    """Test data for .NET CLR Memory with Windows Server showing 8.78% GC time"""
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
            "766573506832",
            "",
            "",
            "761",
            "0",
            "2240904",
            "10000000",
            "12582912",
            "2708256",
            "3461688",
            "124320",
            "60014800",
            "3584288",
            "_Global_",
            "67060776",
            "20831",
            "60934",
            "7064",
            "1038",
            "388",
            "0",
            "392",
            "79908864",
            "805289984",
            "377048032",
            "-1",
            "0",
            "406627",
            "2708256",
            "124320",
            "0",
            "4227247572262",
            "131350801098190000",
        ],
        [
            "0",
            "",
            "",
            "0",
            "0",
            "2240904",
            "10000000",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "sqlservr#3",
            "0",
            "26",
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
            "406627",
            "0",
            "0",
            "0",
            "4227247572262",
            "131350801098190000",
        ],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: StringTable) -> WMISection:
    """Parsed WMI table data"""
    return parse_wmi_table(string_table)


def test_discover_dotnet_clrmemory(parsed: WMISection) -> None:
    """Test discovery function finds Global entry with default parameters"""
    result = list(discover_dotnet_clrmemory(parsed))

    assert len(result) == 1
    item, params = result[0]
    assert item == "_Global_"
    assert params == {}


def test_check_dotnet_clrmemory_global(parsed: WMISection) -> None:
    """Test check function for _Global_ item showing 8.78% GC time"""
    result = list(check_dotnet_clrmemory("_Global_", {"upper": (10.0, 15.0)}, parsed))

    assert len(result) == 1
    state, summary, metrics = result[0]  # type: ignore[misc]

    # Verify state and summary
    assert state == 0
    assert "Time spent in Garbage Collection: 8.78%" in summary

    # Verify metrics
    assert len(metrics) == 1
    metric_name, value, warn, crit, min_val, max_val = metrics[0]  # type: ignore[misc]
    assert metric_name == "percent"
    assert abs(value - 8.778833599942464) < 0.0001  # Check calculated percentage
    assert warn == 10.0
    assert crit == 15.0
    assert min_val == 0
    assert max_val == 100


def test_check_dotnet_clrmemory_sqlservr(parsed: dict[str, Any]) -> None:
    """Test check function for sqlservr#3 item with 0% GC time"""
    result = list(check_dotnet_clrmemory("sqlservr#3", {"upper": (10.0, 15.0)}, parsed))

    assert len(result) == 1
    state, summary, metrics = result[0]  # type: ignore[misc]

    # Verify state and summary
    assert state == 0
    assert "Time spent in Garbage Collection: 0%" in summary

    # Verify metrics
    assert len(metrics) == 1
    metric_name, value, warn, crit, min_val, max_val = metrics[0]  # type: ignore[misc]
    assert metric_name == "percent"
    assert value == 0.0  # Zero GC time for SQL Server process
    assert warn == 10.0
    assert crit == 15.0


def test_check_dotnet_clrmemory_high_gc_warning(parsed: dict[str, Any]) -> None:
    """Test check function with GC time triggering warning"""
    # Use lower thresholds to test warning behavior with 8.78% GC time
    result = list(check_dotnet_clrmemory("_Global_", {"upper": (5.0, 12.0)}, parsed))

    assert len(result) == 1
    state, summary, metrics = result[0]  # type: ignore[misc]

    # Should be WARNING since 8.78% is between 5.0% warn and 12.0% crit
    assert state == 1
    assert "Time spent in Garbage Collection: 8.78%" in summary
    assert "(warn/crit at 5.00%/12.00%)" in summary


def test_check_dotnet_clrmemory_high_gc_critical(parsed: dict[str, Any]) -> None:
    """Test check function with GC time triggering critical"""
    # Use very low thresholds to test critical behavior with 8.78% GC time
    result = list(check_dotnet_clrmemory("_Global_", {"upper": (2.0, 7.0)}, parsed))

    assert len(result) == 1
    state, summary, metrics = result[0]  # type: ignore[misc]

    # Should be CRITICAL since 8.78% > 7.0% critical threshold
    assert state == 2
    assert "Time spent in Garbage Collection: 8.78%" in summary
    assert "(warn/crit at 2.00%/7.00%)" in summary


def test_check_dotnet_clrmemory_nonexistent_item(parsed: dict[str, Any]) -> None:
    """Test check function with non-existent item"""
    result = list(check_dotnet_clrmemory("nonexistent", {"upper": (10.0, 15.0)}, parsed))

    # Should return empty list for non-existent items
    assert len(result) == 0
