#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.windows.agent_based.dotnet_clrmemory import (
    check_dotnet_clrmemory,
    discover_dotnet_clrmemory,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection


@pytest.fixture(name="string_table")
def string_table_fixture() -> StringTable:
    """Test data for .NET CLR Memory with HP Proliant Windows server"""
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
            "687389776176",
            "",
            "",
            "1498",
            "0",
            "2734511",
            "10000000",
            "893649480",
            "8245000",
            "19597152",
            "386480",
            "66266864",
            "10647216",
            "_Global_",
            "96511232",
            "113029",
            "128183",
            "116842",
            "4553",
            "67",
            "616",
            "36628",
            "233213952",
            "22950764544",
            "108935240",
            "-1",
            "0",
            "588533",
            "8245000",
            "386480",
            "0",
            "12303331941741",
            "131097013721920000",
        ],
        [
            "661680",
            "",
            "",
            "0",
            "0",
            "2734511",
            "10000000",
            "4194304",
            "0",
            "24",
            "0",
            "164512",
            "34600",
            "MonitoringHost",
            "199136",
            "42",
            "16",
            "16",
            "0",
            "0",
            "0",
            "1",
            "4358144",
            "4194304",
            "0",
            "-1",
            "5324",
            "588533",
            "0",
            "0",
            "12303331941741",
            "131097013721920000",
        ],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: StringTable) -> WMISection:
    """Parsed WMI table data"""
    return parse_wmi_table(string_table)


def test_discover_dotnet_clrmemory(parsed: WMISection) -> None:
    """Test discovery function finds Global entry with default parameters"""
    result = list(discover_dotnet_clrmemory(parsed))
    assert result == [Service(item="_Global_")]


def test_check_dotnet_clrmemory_global(parsed: WMISection) -> None:
    """Test check function for _Global_ item"""
    result = list(check_dotnet_clrmemory("_Global_", {"upper": (10.0, 15.0)}, parsed))

    assert len(result) == 2
    result_obj, metric = result
    assert isinstance(result_obj, Result)
    assert isinstance(metric, Metric)

    assert result_obj.state == State.OK
    assert "Time spent in Garbage Collection: 2.54%" in result_obj.summary

    assert metric.name == "percent"
    assert abs(metric.value - 2.5363462051694157) < 0.0001
    assert metric.levels == (10.0, 15.0)
    assert metric.boundaries == (0.0, 100.0)


def test_check_dotnet_clrmemory_monitoring_host(parsed: WMISection) -> None:
    """Test check function for MonitoringHost item"""
    result = list(check_dotnet_clrmemory("MonitoringHost", {"upper": (10.0, 15.0)}, parsed))

    assert len(result) == 2
    result_obj, metric = result
    assert isinstance(result_obj, Result)
    assert isinstance(metric, Metric)

    assert result_obj.state == State.OK
    assert "Time spent in Garbage Collection: 0%" in result_obj.summary

    assert metric.name == "percent"
    assert metric.value == 0.0
    assert metric.levels == (10.0, 15.0)


def test_check_dotnet_clrmemory_nonexistent_item(parsed: WMISection) -> None:
    """Test check function with non-existent item"""
    result = list(check_dotnet_clrmemory("nonexistent", {"upper": (10.0, 15.0)}, parsed))
    assert result == []


def test_check_dotnet_clrmemory_high_gc_time(parsed: WMISection) -> None:
    """Test check function with high GC time triggering warning/critical"""
    result = list(check_dotnet_clrmemory("_Global_", {"upper": (1.0, 3.0)}, parsed))

    assert len(result) == 2
    result_obj, _metric = result
    assert isinstance(result_obj, Result)

    assert result_obj.state == State.WARN
    assert "Time spent in Garbage Collection: 2.54%" in result_obj.summary
    assert "(warn/crit at 1.00%/3.00%)" in result_obj.summary


def test_check_dotnet_clrmemory_no_parameters(parsed: WMISection) -> None:
    """Test check function with no upper level parameters"""
    with pytest.raises(KeyError):
        list(check_dotnet_clrmemory("_Global_", {}, parsed))
