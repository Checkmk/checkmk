#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# EXAMPLE DATA FROM: WDC SSC-D0128SC-2100
#<<<smart>>>
#/dev/sda ATA WDC_SSC-D0128SC-   1 Raw_Read_Error_Rate     0x000b   100   100   050    Pre-fail  Always       -       16777215
#/dev/sda ATA WDC_SSC-D0128SC-   3 Spin_Up_Time            0x0007   100   100   050    Pre-fail  Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC-   5 Reallocated_Sector_Ct   0x0013   100   100   050    Pre-fail  Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC-   7 Seek_Error_Rate         0x000b   100   100   050    Pre-fail  Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC-   9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       1408
#/dev/sda ATA WDC_SSC-D0128SC-  10 Spin_Retry_Count        0x0013   100   100   050    Pre-fail  Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC-  12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       523
#/dev/sda ATA WDC_SSC-D0128SC- 168 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1
#/dev/sda ATA WDC_SSC-D0128SC- 175 Program_Fail_Count_Chip 0x0003   100   100   010    Pre-fail  Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC- 192 Power-Off_Retract_Count 0x0012   100   100   000    Old_age   Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC- 194 Temperature_Celsius     0x0022   040   100   000    Old_age   Always       -       40 (Lifetime Min/Max 30/60)
#/dev/sda ATA WDC_SSC-D0128SC- 197 Current_Pending_Sector  0x0012   100   100   000    Old_age   Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC- 240 Head_Flying_Hours       0x0013   100   100   050    Pre-fail  Always       -       0
#/dev/sda ATA WDC_SSC-D0128SC- 170 Unknown_Attribute       0x0003   100   100   010    Pre-fail  Always       -       1769478
#/dev/sda ATA WDC_SSC-D0128SC- 173 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       4217788040605

from typing import Dict, Tuple, Union
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register

# TODO: Need to completely rework smart check. Use IDs instead of changing
# descriptions! But be careful: There is no standard neither for IDs nor for
# descriptions. Only use those, which are common sense.

Disk = Dict[str, Union[str, int, Tuple[int, int]]]

Section = Dict[str, Disk]


def parse_raw_values(string_table: StringTable) -> Section:
    """
        >>> from pprint import pprint
        >>> pprint(parse_raw_values([
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '1', 'Raw_Read_Error_Rate',
        ...      '0x000b', '100', '100', '050', 'Pre-fail', 'Always', '-', '16777215'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '3', 'Spin_Up_Time',
        ...      '0x0007', '100', '100', '050', 'Pre-fail', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '5', 'Reallocated_Sector_Ct',
        ...      '0x0013', '100', '100', '050', 'Pre-fail', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '7', 'Seek_Error_Rate',
        ...      '0x000b', '100', '100', '050', 'Pre-fail', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '9', 'Power_On_Hours',
        ...      '0x0012', '100', '100', '000', 'Old_age', 'Always', '-', '1408'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '10', 'Spin_Retry_Count',
        ...      '0x0013', '100', '100', '050', 'Pre-fail', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '12', 'Power_Cycle_Count',
        ...      '0x0012', '100', '100', '000', 'Old_age', 'Always', '-', '523'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '168', 'Unknown_Attribute',
        ...      '0x0012', '100', '100', '000', 'Old_age', 'Always', '-', '1'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '175', 'Program_Fail_Count_Chip',
        ...      '0x0003', '100', '100', '010', 'Pre-fail', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '192', 'Power-Off_Retract_Count',
        ...      '0x0012', '100', '100', '000', 'Old_age', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '194', 'Temperature_Celsius',
        ...      '0x0022', '040', '100', '000', 'Old_age', 'Always', '-', '40', '(Lifetime', 'Min/Max', '30/60)'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '197', 'Current_Pending_Sector',
        ...      '0x0012', '100', '100', '000', 'Old_age', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '240', 'Head_Flying_Hours',
        ...      '0x0013', '100', '100', '050', 'Pre-fail', 'Always', '-', '0'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '170', 'Unknown_Attribute',
        ...      '0x0003', '100', '100', '010', 'Pre-fail', 'Always', '-', '1769478'],
        ...     ['/dev/sda', 'ATA', 'WDC_SSC-D0128SC-', '173', 'Unknown_Attribute',
        ...      '0x0012', '100', '100', '000', 'Old_age', 'Always', '-', '4217788040605'],
        ... ]))
        {'/dev/sda': {'Current_Pending_Sector': 0,
                      'Head_Flying_Hours': 0,
                      'Power-Off_Retract_Count': 0,
                      'Power_Cycle_Count': 523,
                      'Power_On_Hours': 1408,
                      'Program_Fail_Count_Chip': 0,
                      'Raw_Read_Error_Rate': 16777215,
                      'Reallocated_Sector_Ct': 0,
                      'Seek_Error_Rate': 0,
                      'Spin_Retry_Count': 0,
                      'Spin_Up_Time': 0,
                      'Temperature_Celsius': 40}}

    """
    disks: Section = {}

    for line in string_table:
        if len(line) >= 13:
            disk = disks.setdefault(line[0], {})

            field = line[4]
            if field == "Unknown_Attribute":
                continue
            try:
                disk[field] = int(line[12])
            except ValueError:
                disk[field] = 0

            if field == "Reallocated_Event_Count":  # special case, see check function
                try:
                    disk["_normalized_Reallocated_Event_Count"] = int(line[6]), int(line[8])
                except ValueError:
                    pass

        # nvme
        elif 3 <= len(line) <= 6:
            if "/dev" in line[0]:
                disk = disks.setdefault(line[0], {})
                continue

            field, value = [e.strip() for e in " ".join(line).split(":")]
            value = value.replace("%", "").replace(".", "").replace(",", "")
            if field == "Temperature":
                value = value.split()[0]
            if field == "Critical Warning":
                value = int(value, 16)  # type: ignore[assignment]
            if field == "Data Units Read":
                value = (int(value.split()[0]) * 512000)  # type: ignore[assignment]
            if field == "Data Units Written":
                value = (int(value.split()[0]) * 512000)  # type: ignore[assignment]
            try:
                disk[field.replace(" ", "_")] = int(value)
            except ValueError:
                disk[field.replace(" ", "_")] = 0

    return disks


register.agent_section(
    name="smart",
    parse_function=parse_raw_values,
)
