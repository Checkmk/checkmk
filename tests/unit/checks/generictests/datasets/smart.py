#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based import smart

checkname = 'smart'

parsed = smart.parse_raw_values(
    [[
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
     ], [u'/dev/nvme0n1', u'NVME', u'SAMSUNG_MZQLW960HMJP-00003'],
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
     [u'Temperature', u'Sensor', u'1:', u'39', u'Celsius']])

discovery = {
    'temp': [(u'/dev/nvme0n1', {}), (u'/dev/sda', {})]
}

checks = {
    'temp': [(u'/dev/nvme0n1', {
        'levels': (35, 40)
    }, [
        (1, '39 \xb0C (warn/crit at 35/40 \xb0C)', [('temp', 39, 35, 40, None, None)]),
    ]),],
}
