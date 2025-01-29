#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import (
    GetRateError,
    IgnoreResults,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import smart

STRING_TABLE_SD = [
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "5",
        "Reallocated_Sector_Ct",
        "0x0033",
        "100",
        "100",
        "010",
        "Pre-fail",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "9",
        "Power_On_Hours",
        "0x0032",
        "099",
        "099",
        "000",
        "Old_age",
        "Always",
        "-",
        "1609",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "12",
        "Power_Cycle_Count",
        "0x0032",
        "099",
        "099",
        "000",
        "Old_age",
        "Always",
        "-",
        "9",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "177",
        "Wear_Leveling_Count",
        "0x0013",
        "099",
        "099",
        "005",
        "Pre-fail",
        "Always",
        "-",
        "1",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "179",
        "Used_Rsvd_Blk_Cnt_Tot",
        "0x0013",
        "100",
        "100",
        "010",
        "Pre-fail",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "180",
        "Unused_Rsvd_Blk_Cnt_Tot",
        "0x0013",
        "100",
        "100",
        "010",
        "Pre-fail",
        "Always",
        "-",
        "13127",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "181",
        "Program_Fail_Cnt_Total",
        "0x0032",
        "100",
        "100",
        "010",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "182",
        "Erase_Fail_Count_Total",
        "0x0032",
        "100",
        "100",
        "010",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "183",
        "Runtime_Bad_Block",
        "0x0013",
        "100",
        "100",
        "010",
        "Pre-fail",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "184",
        "End-to-End_Error",
        "0x0033",
        "100",
        "100",
        "097",
        "Pre-fail",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "187",
        "Reported_Uncorrect",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "188",
        "Command_Timeout",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "194",
        "Temperature_Celsius",
        "0x0022",
        "061",
        "052",
        "000",
        "Old_age",
        "Always",
        "-",
        "39",
        "(Min/Max",
        "31/49)",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "195",
        "Hardware_ECC_Recovered",
        "0x001a",
        "200",
        "200",
        "000",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "197",
        "Current_Pending_Sector",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "199",
        "UDMA_CRC_Error_Count",
        "0x003e",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "202",
        "Unknown_SSD_Attribute",
        "0x0033",
        "100",
        "100",
        "010",
        "Pre-fail",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "235",
        "Unknown_Attribute",
        "0x0012",
        "099",
        "099",
        "000",
        "Old_age",
        "Always",
        "-",
        "5",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "241",
        "Total_LBAs_Written",
        "0x0032",
        "099",
        "099",
        "000",
        "Old_age",
        "Always",
        "-",
        "7655764477",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "242",
        "Total_LBAs_Read",
        "0x0032",
        "099",
        "099",
        "000",
        "Old_age",
        "Always",
        "-",
        "10967739912",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "243",
        "Unknown_Attribute",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "244",
        "Unknown_Attribute",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "0",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "245",
        "Unknown_Attribute",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "65535",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "246",
        "Unknown_Attribute",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "65535",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "247",
        "Unknown_Attribute",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "65535",
    ],
    [
        "/dev/sda",
        "ATA",
        "SAMSUNG_MZ7LM3T8",
        "251",
        "Unknown_Attribute",
        "0x0032",
        "100",
        "100",
        "000",
        "Old_age",
        "Always",
        "-",
        "14938006528",
    ],
]

STRING_TABLE_NVME = [
    ["/dev/nvme0n1", "NVME", "SAMSUNG_MZQLW960HMJP-00003"],
    ["Critical", "Warning:", "0x00"],
    ["Temperature:", "39", "Celsius"],
    ["Available", "Spare:", "100%"],
    ["Available", "Spare", "Threshold:", "10%"],
    ["Percentage", "Used:", "0%"],
    ["Data", "Units", "Read:", "5.125.696", "[2,62", "TB]"],
    ["Data", "Units", "Written:", "4.566.369", "[2,33", "TB]"],
    ["Host", "Read", "Commands:", "544.752.409"],
    ["Host", "Write", "Commands:", "113.831.833"],
    ["Controller", "Busy", "Time:", "221"],
    ["Power", "Cycles:", "8"],
    ["Power", "On", "Hours:", "1.609"],
    ["Unsafe", "Shutdowns:", "5"],
    ["Media", "and", "Data", "Integrity", "Errors:", "0"],
    ["Error", "Information", "Log", "Entries:", "0"],
    ["Warning", "Comp.", "Temperature", "Time:", "0"],
    ["Critical", "Comp.", "Temperature", "Time:", "0"],
    ["Temperature", "Sensor", "1:", "39", "Celsius"],
]

SECTION_SD = {
    "/dev/sda": {
        "Command_Timeout_Counter": 0,
        "Pending_Sectors": 0,
        "End-to-End_Errors": 0,
        "Erase_Fail_Count_Total": 0,
        "Hardware_ECC_Recovered": 0,
        "Power_Cycles": 9,
        "Power_On_Hours": 1609,
        "Program_Fail_Cnt_Total": 0,
        "Reallocated_Sectors": 0,
        "Uncorrectable_Errors": 0,
        "Runtime_Bad_Block": 0,
        "Temperature": 39,
        "Total_LBAs_Read": 10967739912,
        "Total_LBAs_Written": 7655764477,
        "UDMA_CRC_Errors": 0,
        "Unknown_SSD_Attribute": 0,
        "Unused_Rsvd_Blk_Cnt_Tot": 13127,
        "Used_Rsvd_Blk_Cnt_Tot": 0,
        "Wear_Leveling_Count": 1,
    },
}

SECTION_NVME = {
    "/dev/nvme0n1": {
        "Available_Spare": 100,
        "Available_Spare_Threshold": 10,
        "Controller_Busy_Time": 221,
        "Critical_Comp._Temperature_Time": 0,
        "Critical_Warning": 0,
        "Data_Units_Read": 2624356352000,
        "Data_Units_Written": 2337980928000,
        "Error_Information_Log_Entries": 0,
        "Host_Read_Commands": 544752409,
        "Host_Write_Commands": 113831833,
        "Media_and_Data_Integrity_Errors": 0,
        "Percentage_Used": 0,
        "Power_Cycles": 8,
        "Power_On_Hours": 1609,
        "Temperature": 39,
        "Temperature_Sensor_1": 0,
        "Unsafe_Shutdowns": 5,
        "Warning_Comp._Temperature_Time": 0,
    },
}

# attributes not relevant for the smart check
SECTION_WITH_TEMPERATURE_ONLY = {
    "/dev/nvme0n1": {
        "Temperature": 39,
    }
}


@pytest.mark.parametrize(
    "string_table, section", [(STRING_TABLE_SD, SECTION_SD), (STRING_TABLE_NVME, SECTION_NVME)]
)
def test_parse_smart(string_table: StringTable, section: smart.Section) -> None:
    assert smart.parse_raw_values(string_table) == section


@pytest.mark.parametrize(
    "section, discovered",
    [
        pytest.param(
            SECTION_SD,
            [
                Service(
                    item="/dev/sda",
                    parameters={
                        "Command_Timeout_Counter": 0,
                        "Pending_Sectors": 0,
                        "End-to-End_Errors": 0,
                        "Reallocated_Sectors": 0,
                        "Uncorrectable_Errors": 0,
                        "UDMA_CRC_Errors": 0,
                    },
                ),
            ],
            id="SD",
        ),
        pytest.param(
            SECTION_NVME,
            [
                Service(
                    item="/dev/nvme0n1",
                    parameters={
                        "Critical_Warning": 0,
                        "Media_and_Data_Integrity_Errors": 0,
                    },
                ),
            ],
            id="NVME",
        ),
        pytest.param(
            SECTION_WITH_TEMPERATURE_ONLY,
            [],
            id="No service discovered",
        ),
    ],
)
def test_discover_smart_stats(section: smart.Section, discovered: Sequence[Service]) -> None:
    assert list(smart.discover_smart_stats(section)) == discovered


@pytest.mark.parametrize(
    "item, params, section, result",
    [
        (
            "/dev/sda",
            {
                "Pending_Sectors": 0,
                "End-to-End_Errors": 0,
                "Reallocated_Sectors": 0,
                "Uncorrectable_Errors": 0,
                "UDMA_CRC_Errors": 0,
            },
            SECTION_SD,
            [
                Result(state=State.OK, summary="Reallocated sectors: 0"),
                Metric("Reallocated_Sectors", 0),
                Result(state=State.OK, summary="Powered on: 67 days 1 hour"),
                Metric("Power_On_Hours", 1609),
                Result(state=State.OK, summary="Power cycles: 9"),
                Metric("Power_Cycles", 9),
                Result(state=State.OK, summary="End-to-End errors: 0"),
                Metric("End-to-End_Errors", 0),
                Result(state=State.OK, summary="Uncorrectable errors: 0"),
                Metric("Uncorrectable_Errors", 0),
                Result(state=State.OK, summary="Command timeout counter: 0"),
                Metric("Command_Timeout_Counter", 0.0),
                Result(state=State.OK, summary="Pending sectors: 0"),
                Metric("Pending_Sectors", 0),
                Result(state=State.OK, summary="UDMA CRC errors: 0"),
                Metric("UDMA_CRC_Errors", 0),
            ],
        ),
        (
            "/dev/nvme0n1",
            {"Critical_Warning": 0},
            SECTION_NVME,
            [
                Result(state=State.OK, summary="Powered on: 67 days 1 hour"),
                Metric("Power_On_Hours", 1609),
                Result(state=State.OK, summary="Power cycles: 8"),
                Metric("Power_Cycles", 8),
                Result(state=State.OK, summary="Critical warning: 0"),
                Metric("Critical_Warning", 0),
                Result(state=State.OK, summary="Media and data integrity errors: 0"),
                Metric("Media_and_Data_Integrity_Errors", 0),
                Result(state=State.OK, summary="Available spare: 100.00%"),
                Metric("Available_Spare", 100),
                Result(state=State.OK, summary="Percentage used: 0%"),
                Metric("Percentage_Used", 0),
                Result(state=State.OK, summary="Error information log entries: 0"),
                Metric("Error_Information_Log_Entries", 0),
                Result(state=State.OK, summary="Data units read: 2.39 TiB"),
                Metric("Data_Units_Read", 2624356352000),
                Result(state=State.OK, summary="Data units written: 2.13 TiB"),
                Metric("Data_Units_Written", 2337980928000),
            ],
        ),
    ],
)
def test_check_smart_stats(
    item: str,
    params: Mapping[str, int],
    section: smart.Section,
    result: Sequence[IgnoreResults | Metric | Result],
) -> None:
    assert list(smart.check_smart_stats(item, params, section)) == result


@pytest.mark.usefixtures("initialised_item_state")
def test_check_smart_command_timeout_rate() -> None:
    section_timeout = {"/dev/sda": {"Command_Timeout_Counter": 0}}
    now_simulated = 581792400
    with (
        pytest.raises(GetRateError),
        time_machine.travel(datetime.datetime.fromtimestamp(now_simulated, tz=ZoneInfo("UTC"))),
    ):
        list(smart.check_smart_stats("/dev/sda", {"Command_Timeout_Counter": 0}, section_timeout))

    # Simulate an accepted increment rate of the counter
    thirty_min_later = now_simulated + 30 * 60
    section_timeout["/dev/sda"]["Command_Timeout_Counter"] = 1
    with time_machine.travel(datetime.datetime.fromtimestamp(thirty_min_later, tz=ZoneInfo("UTC"))):
        assert list(
            smart.check_smart_stats("/dev/sda", {"Command_Timeout_Counter": 0}, section_timeout)
        ) == [
            Result(state=State.OK, summary="Command timeout counter: 1"),
            Metric("Command_Timeout_Counter", 1.0),
        ]

    # Simulate an exceeding rate for command timeouts
    ten_sec_later = thirty_min_later + 10
    section_timeout["/dev/sda"]["Command_Timeout_Counter"] = 5
    with time_machine.travel(datetime.datetime.fromtimestamp(ten_sec_later, tz=ZoneInfo("UTC"))):
        assert list(
            smart.check_smart_stats("/dev/sda", {"Command_Timeout_Counter": 0}, section_timeout)
        ) == [
            Result(
                state=State.CRIT,
                summary=(
                    "Command timeout counter: 5 "
                    "(counter increased more than 100 counts / h (!!). "
                    "Value during discovery was: 0)"
                ),
            ),
            Metric("Command_Timeout_Counter", 5),
        ]


def test_parse_duplicate_output_correctly() -> None:
    # Werk 16871 causes duplicate output for ATA devices, if they output data for both
    # `smartctl -d ata -v 9,raw48 -A $D` and `smartctl -d sat -v 9,raw48 -A $D`
    # Ensure behaviour is unaffected on the check side.
    assert smart.parse_raw_values(STRING_TABLE_SD + STRING_TABLE_SD) == SECTION_SD
