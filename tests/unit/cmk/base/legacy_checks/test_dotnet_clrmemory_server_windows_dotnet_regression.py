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
Test regression scenarios for .NET CLR Memory monitoring showing 1.84% GC time.
This test covers the dotnet_clrmemory check with WMI data from a Windows server
showing _Global_ instance with moderate garbage collection overhead.
"""

import pytest

from cmk.base.legacy_checks.dotnet_clrmemory import (
    check_dotnet_clrmemory,
    discover_dotnet_clrmemory,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection


@pytest.fixture(name="test_data")
def fixture_test_data() -> list[list[str]]:
    """WMI data for .NET CLR Memory regression test with 1.84% GC time."""
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
            "21380464834160",
            "",
            "",
            "13821",
            "0",
            "14318180",
            "10000000",
            "2012417216",
            "4762504",
            "28497416",
            "718488",
            "257543384",
            "239855984",
            "_Global_",
            "525896784",
            "45499",
            "894395",
            "717878",
            "531223",
            "68441",
            "2517",
            "3222",
            "2800212096",
            "64290166912",
            "78964360",
            "-1",
            "0",
            "491512",
            "4762504",
            "718488",
            "0",
            "57866201615573",
            "131407819020030000",
        ],
        [
            "1034323144",
            "",
            "",
            "421",
            "0",
            "14318180",
            "10000000",
            "13107200",
            "0",
            "1041864",
            "0",
            "12959776",
            "8008032",
            "powershell",
            "22009672",
            "3195",
            "64",
            "6",
            "4",
            "0",
            "34",
            "47",
            "75497472",
            "2155872256",
            "0",
            "453642218",
            "8544",
            "0",
            "0",
            "0",
            "0",
            "57866201615573",
            "131407819020030000",
        ],
        [
            "26556067040",
            "",
            "",
            "12972",
            "0",
            "14318180",
            "10000000",
            "171793984",
            "1121296",
            "1121488",
            "1008",
            "8512416",
            "6165288",
            "w3wp",
            "15799192",
            "1267",
            "339",
            "121",
            "7",
            "0",
            "214",
            "47",
            "188348800",
            "5368707456",
            "6451",
            "453642218",
            "8544",
            "40072",
            "1121296",
            "1008",
            "0",
            "57866201615573",
            "131407819020030000",
        ],
        [
            "28505439528",
            "",
            "",
            "35",
            "0",
            "14318180",
            "10000000",
            "171793984",
            "35560",
            "6990272",
            "0",
            "82755208",
            "2618360",
            "Microsoft.Exchange.EdgeSyncSvc",
            "19863824",
            "939",
            "1043",
            "109",
            "38",
            "0",
            "142",
            "13",
            "294911520",
            "2415919104",
            "0",
            "453642218",
            "8584",
            "35560",
            "35560",
            "0",
            "0",
            "57866201615573",
            "131407819020030000",
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
    """Test check of _Global_ instance showing 1.84% GC time."""
    check_result = list(check_dotnet_clrmemory("_Global_", {"upper": (10.0, 15.0)}, parsed_wmi))

    assert len(check_result) == 1
    status, message, perfdata = check_result[0]  # type: ignore[misc]

    assert status == 0  # OK state
    assert "Time spent in Garbage Collection: 1.84%" in message
    assert len(perfdata) == 1
    assert perfdata[0][0] == "percent"
    # Check that the percentage is approximately 1.84%
    assert abs(perfdata[0][1] - 1.8385322768796544) < 0.001
    assert perfdata[0][2] == 10.0  # type: ignore[misc]
    assert perfdata[0][3] == 15.0  # type: ignore[misc]


def test_dotnet_clrmemory_threshold_warning(parsed_wmi: WMISection) -> None:
    """Test warning threshold behavior."""
    # Set lower thresholds to trigger warning
    check_result = list(check_dotnet_clrmemory("_Global_", {"upper": (1.0, 2.0)}, parsed_wmi))

    assert len(check_result) == 1
    status, message, perfdata = check_result[0]  # type: ignore[misc]

    assert status == 1  # Warning state
    assert "Time spent in Garbage Collection: 1.84%" in message


def test_dotnet_clrmemory_threshold_critical(parsed_wmi: WMISection) -> None:
    """Test critical threshold behavior."""
    # Set very low thresholds to trigger critical
    check_result = list(check_dotnet_clrmemory("_Global_", {"upper": (0.5, 1.0)}, parsed_wmi))

    assert len(check_result) == 1
    status, message, perfdata = check_result[0]  # type: ignore[misc]

    assert status == 2  # Critical state
    assert "Time spent in Garbage Collection: 1.84%" in message


def test_dotnet_clrmemory_nonexistent_item(parsed_wmi: WMISection) -> None:
    """Test check of non-existent instance."""
    check_result = list(check_dotnet_clrmemory("NonExistent", {"upper": (10.0, 15.0)}, parsed_wmi))
    assert len(check_result) == 0  # No results for non-existent instance
