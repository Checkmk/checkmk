#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based import smart
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


STRING_TABLE_SD = [
    [
        u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'5', u'Reallocated_Sector_Ct', u'0x0033', u'100',
        u'100', u'010', u'Pre-fail', u'Always', u'-', u'0'
    ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'9', u'Power_On_Hours', u'0x0032', u'099',
         u'099', u'000', u'Old_age', u'Always', u'-', u'1609'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'12', u'Power_Cycle_Count', u'0x0032', u'099',
         u'099', u'000', u'Old_age', u'Always', u'-', u'9'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'177', u'Wear_Leveling_Count', u'0x0013',
         u'099', u'099', u'005', u'Pre-fail', u'Always', u'-', u'1'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'179', u'Used_Rsvd_Blk_Cnt_Tot', u'0x0013',
         u'100', u'100', u'010', u'Pre-fail', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'180', u'Unused_Rsvd_Blk_Cnt_Tot', u'0x0013',
         u'100', u'100', u'010', u'Pre-fail', u'Always', u'-', u'13127'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'181', u'Program_Fail_Cnt_Total', u'0x0032',
         u'100', u'100', u'010', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'182', u'Erase_Fail_Count_Total', u'0x0032',
         u'100', u'100', u'010', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'183', u'Runtime_Bad_Block', u'0x0013', u'100',
         u'100', u'010', u'Pre-fail', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'184', u'End-to-End_Error', u'0x0033', u'100',
         u'100', u'097', u'Pre-fail', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'187', u'Reported_Uncorrect', u'0x0032', u'100',
         u'100', u'000', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'194', u'Temperature_Celsius', u'0x0022',
         u'061', u'052', u'000', u'Old_age', u'Always', u'-', u'39', u'(Min/Max', u'31/49)'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'195', u'Hardware_ECC_Recovered', u'0x001a',
         u'200', u'200', u'000', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'197', u'Current_Pending_Sector', u'0x0032',
         u'100', u'100', u'000', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'199', u'UDMA_CRC_Error_Count', u'0x003e',
         u'100', u'100', u'000', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'202', u'Unknown_SSD_Attribute', u'0x0033',
         u'100', u'100', u'010', u'Pre-fail', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'235', u'Unknown_Attribute', u'0x0012', u'099',
         u'099', u'000', u'Old_age', u'Always', u'-', u'5'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'241', u'Total_LBAs_Written', u'0x0032', u'099',
         u'099', u'000', u'Old_age', u'Always', u'-', u'7655764477'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'242', u'Total_LBAs_Read', u'0x0032', u'099',
         u'099', u'000', u'Old_age', u'Always', u'-', u'10967739912'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'243', u'Unknown_Attribute', u'0x0032', u'100',
         u'100', u'000', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'244', u'Unknown_Attribute', u'0x0032', u'100',
         u'100', u'000', u'Old_age', u'Always', u'-', u'0'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'245', u'Unknown_Attribute', u'0x0032', u'100',
         u'100', u'000', u'Old_age', u'Always', u'-', u'65535'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'246', u'Unknown_Attribute', u'0x0032', u'100',
         u'100', u'000', u'Old_age', u'Always', u'-', u'65535'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'247', u'Unknown_Attribute', u'0x0032', u'100',
         u'100', u'000', u'Old_age', u'Always', u'-', u'65535'
     ],
     [
         u'/dev/sda', u'ATA', u'SAMSUNG_MZ7LM3T8', u'251', u'Unknown_Attribute', u'0x0032', u'100',
         u'100', u'000', u'Old_age', u'Always', u'-', u'14938006528'
     ],
]

STRING_TABLE_NVME = [
    [u'/dev/nvme0n1', u'NVME', u'SAMSUNG_MZQLW960HMJP-00003'],
    [u'Critical', u'Warning:', u'0x00'], [u'Temperature:', u'39', u'Celsius'],
    [u'Available', u'Spare:', u'100%'], [u'Available', u'Spare', u'Threshold:', u'10%'],
    [u'Percentage', u'Used:', u'0%'],
    [u'Data', u'Units', u'Read:', u'5.125.696', u'[2,62', u'TB]'],
    [u'Data', u'Units', u'Written:', u'4.566.369', u'[2,33', u'TB]'],
    [u'Host', u'Read', u'Commands:', u'544.752.409'],
    [u'Host', u'Write', u'Commands:', u'113.831.833'], [u'Controller', u'Busy', u'Time:', u'221'],
    [u'Power', u'Cycles:', u'8'], [u'Power', u'On', u'Hours:', u'1.609'],
    [u'Unsafe', u'Shutdowns:', u'5'], [u'Media', u'and', u'Data', u'Integrity', u'Errors:', u'0'],
    [u'Error', u'Information', u'Log', u'Entries:', u'0'],
    [u'Warning', u'Comp.', u'Temperature', u'Time:', u'0'],
    [u'Critical', u'Comp.', u'Temperature', u'Time:', u'0'],
    [u'Temperature', u'Sensor', u'1:', u'39', u'Celsius'],
]


SECTION_SD = {
    '/dev/sda': {
        'Current_Pending_Sector': 0,
         'End-to-End_Error': 0,
         'Erase_Fail_Count_Total': 0,
         'Hardware_ECC_Recovered': 0,
         'Power_Cycle_Count': 9,
         'Power_On_Hours': 1609,
         'Program_Fail_Cnt_Total': 0,
         'Reallocated_Sector_Ct': 0,
         'Reported_Uncorrect': 0,
         'Runtime_Bad_Block': 0,
         'Temperature_Celsius': 39,
         'Total_LBAs_Read': 10967739912,
         'Total_LBAs_Written': 7655764477,
         'UDMA_CRC_Error_Count': 0,
         'Unknown_SSD_Attribute': 0,
         'Unused_Rsvd_Blk_Cnt_Tot': 13127,
         'Used_Rsvd_Blk_Cnt_Tot': 0,
         'Wear_Leveling_Count': 1
    },
}


SECTION_NVME = {
    '/dev/nvme0n1': {
        'Available_Spare': 100,
        'Available_Spare_Threshold': 10,
        'Controller_Busy_Time': 221,
        'Critical_Comp._Temperature_Time': 0,
        'Critical_Warning': 0,
        'Data_Units_Read': 2624356352000,
        'Data_Units_Written': 2337980928000,
        'Error_Information_Log_Entries': 0,
        'Host_Read_Commands': 544752409,
        'Host_Write_Commands': 113831833,
        'Media_and_Data_Integrity_Errors': 0,
        'Percentage_Used': 0,
        'Power_Cycles': 8,
        'Power_On_Hours': 1609,
        'Temperature': 39,
        'Temperature_Sensor_1': 0,
        'Unsafe_Shutdowns': 5,
        'Warning_Comp._Temperature_Time': 0
    },
}


@pytest.mark.parametrize("string_table, section", [
    (STRING_TABLE_SD, SECTION_SD),
    (STRING_TABLE_NVME, SECTION_NVME)
])
def test_parse_smart(string_table, section):
    assert smart.parse_raw_values(string_table) == section


@pytest.mark.parametrize("section, discovered", [
    (SECTION_SD, [
        Service(
            item='/dev/sda',
            parameters={
                'Current_Pending_Sector': 0,
                'End-to-End_Error': 0,
                'Reallocated_Sector_Ct': 0,
                'Reported_Uncorrect': 0,
                'UDMA_CRC_Error_Count': 0
            },
        ),
    ]),
    (SECTION_NVME, [
        Service(
            item='/dev/nvme0n1',
            parameters={
                'Critical_Warning': 0,
            },
        ),
    ]),
])
def test_discover_smart_stats(section, discovered):
    assert list(smart.discover_smart_stats(section)) == discovered


@pytest.mark.parametrize("item, params, section, result", [
    ("/dev/sda", {
        'Current_Pending_Sector': 0,
        'End-to-End_Error': 0,
        'Reallocated_Sector_Ct': 0,
        'Reported_Uncorrect': 0,
        'UDMA_CRC_Error_Count': 0,
    }, SECTION_SD, [
        Result(state=State.OK, summary='Powered on: 67 days 1 hour'),
        Metric('Power_On_Hours', 1609),
        Result(state=State.OK, summary='Power cycles: 9'),
        Metric('Power_Cycle_Count', 9),
        Result(state=State.OK, summary='Uncorrectable errors: 0'),
        Metric('Reported_Uncorrect', 0),
        Result(state=State.OK, notice='Reallocated sectors: 0'),
        Metric('Reallocated_Sector_Ct', 0),
        Result(state=State.OK, notice='Pending sectors: 0'),
        Metric('Current_Pending_Sector', 0),
        Result(state=State.OK, notice='End-to-End errors: 0'),
        Metric('End-to-End_Error', 0),
        Result(state=State.OK, notice='UDMA CRC errors: 0'),
        Metric('UDMA_CRC_Error_Count', 0),
    ]),
    ("/dev/nvme0n1", {'Critical_Warning': 0}, SECTION_NVME, [
        Result(state=State.OK, summary='Powered on: 67 days 1 hour'),
        Metric('Power_On_Hours', 1609),
        Result(state=State.OK, summary='Power cycles: 8'),
        Metric('Power_Cycles', 8),
        Result(state=State.OK, notice='Critical warning: 0'),
        Metric('Critical_Warning', 0),
        Result(state=State.OK, notice='Available spare: 100%'),
        Metric('Available_Spare', 100),
        Result(state=State.OK, notice='Percentage used: 0%'),
        Metric('Percentage_Used', 0),
        Result(state=State.OK, summary='Media and data integrity errors: 0'),
        Metric('Media_and_Data_Integrity_Errors', 0),
        Result(state=State.OK, notice='Error information log entries: 0'),
        Metric('Error_Information_Log_Entries', 0),
        Result(state=State.OK, notice='Data units read: 2.39 TiB'),
        Metric('Data_Units_Read', 2624356352000),
        Result(state=State.OK, notice='Data units written: 2.13 TiB'),
        Metric('Data_Units_Written', 2337980928000),
    ]),
])
def test_check_smart_stats(item, params, section, result):
    assert list(smart.check_smart_stats(item, params, section)) == result
