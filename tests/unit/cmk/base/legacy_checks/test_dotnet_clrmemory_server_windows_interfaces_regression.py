#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""
Test regression scenarios for .NET CLR Memory monitoring showing 4.08% GC time.
This test covers the dotnet_clrmemory check with WMI data from a Windows server
showing _Global_ instance with higher garbage collection overhead.
"""

import pytest

from cmk.base.legacy_checks.dotnet_clrmemory import (
    check_dotnet_clrmemory,
    discover_dotnet_clrmemory,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection


@pytest.fixture(name="test_data")
def fixture_test_data() -> list[list[str]]:
    """WMI data for .NET CLR Memory regression test with 4.08% GC time."""
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
            "342508834992",
            "",
            "",
            "3200",
            "0",
            "14318180",
            "10000000",
            "433175112",
            "23101720",
            "35139360",
            "3347712",
            "59379192",
            "21526728",
            "_Global_",
            "116045280",
            "40551",
            "6458",
            "2250",
            "1302",
            "86",
            "110",
            "8487",
            "266633216",
            "9663578112",
            "175321424",
            "-1",
            "0",
            "313116",
            "23101720",
            "3347712",
            "0",
            "18557575439465",
            "131407216716290000",
        ],
        [
            "70522792",
            "",
            "",
            "253",
            "0",
            "14318180",
            "10000000",
            "29636664",
            "633280",
            "645880",
            "3347712",
            "4912856",
            "939496",
            "powershell",
            "8831224",
            "1344",
            "198",
            "39",
            "13",
            "0",
            "10",
            "52",
            "36143104",
            "1073737728",
            "0",
            "689347",
            "3872",
            "0",
            "633280",
            "3347712",
            "0",
            "18557575439465",
            "131407216716290000",
        ],
        [
            "272026042680",
            "",
            "",
            "2947",
            "0",
            "14318180",
            "10000000",
            "403538448",
            "22468440",
            "34493480",
            "0",
            "54466336",
            "20587232",
            "w3wp",
            "107214272",
            "39207",
            "6260",
            "2211",
            "1289",
            "86",
            "100",
            "8435",
            "230489600",
            "8589930496",
            "175321424",
            "689347",
            "3132",
            "313116",
            "22468440",
            "0",
            "0",
            "18557575439465",
            "131407216716290000",
        ],
        [
            "7909916312",
            "",
            "",
            "469",
            "0",
            "14318180",
            "10000000",
            "6291456",
            "974888",
            "1668344",
            "0",
            "20297936",
            "2014816",
            "WmiPrvSE",
            "23981096",
            "22337",
            "1230",
            "363",
            "13",
            "0",
            "0",
            "6770",
            "29421568",
            "402644992",
            "48875",
            "689347",
            "2708",
            "17108",
            "974888",
            "0",
            "0",
            "18557575439465",
            "131407216716290000",
        ],
    ]


@pytest.fixture(name="parsed_wmi")
def fixture_parsed_wmi(test_data: list[list[str]]) -> WMISection:
    """Parse the WMI data into a WMITable object."""
    return parse_wmi_table(test_data)


def test_dotnet_clrmemory_discovery(parsed_wmi: WMISection) -> None:
    """Test discovery of .NET CLR Memory instances."""
    discovery_result = list(discover_dotnet_clrmemory(parsed_wmi))
    assert len(discovery_result) == 1
    assert discovery_result[0] == ("_Global_", {})


def test_dotnet_clrmemory_check_global_instance(parsed_wmi: WMISection) -> None:
    """Test check of _Global_ instance showing 4.08% GC time."""
    check_result = list(check_dotnet_clrmemory("_Global_", {"upper": (10.0, 15.0)}, parsed_wmi))

    assert len(check_result) == 1
    status, message, perfdata = check_result[0]  # type: ignore[misc]

    assert status == 0  # OK state
    assert "Time spent in Garbage Collection: 4.08%" in message
    assert len(perfdata) == 1
    assert perfdata[0][0] == "percent"
    # Check that the percentage is approximately 4.08%
    assert abs(perfdata[0][1] - 4.082020000573718) < 0.001
    assert perfdata[0][2] == 10.0  # type: ignore[misc]
    assert perfdata[0][3] == 15.0  # type: ignore[misc]


def test_dotnet_clrmemory_threshold_warning(parsed_wmi: WMISection) -> None:
    """Test warning threshold behavior."""
    # Set lower thresholds to trigger warning
    check_result = list(check_dotnet_clrmemory("_Global_", {"upper": (3.0, 5.0)}, parsed_wmi))

    assert len(check_result) == 1
    status, message, perfdata = check_result[0]  # type: ignore[misc]

    assert status == 1  # Warning state
    assert "Time spent in Garbage Collection: 4.08%" in message


def test_dotnet_clrmemory_threshold_critical(parsed_wmi: WMISection) -> None:
    """Test critical threshold behavior."""
    # Set very low thresholds to trigger critical
    check_result = list(check_dotnet_clrmemory("_Global_", {"upper": (2.0, 3.0)}, parsed_wmi))

    assert len(check_result) == 1
    status, message, perfdata = check_result[0]  # type: ignore[misc]

    assert status == 2  # Critical state
    assert "Time spent in Garbage Collection: 4.08%" in message


def test_dotnet_clrmemory_nonexistent_item(parsed_wmi: WMISection) -> None:
    """Test check of non-existent instance."""
    check_result = list(check_dotnet_clrmemory("NonExistent", {"upper": (10.0, 15.0)}, parsed_wmi))
    assert len(check_result) == 0  # No results for non-existent instance
