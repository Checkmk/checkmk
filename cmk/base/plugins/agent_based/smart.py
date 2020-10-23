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

from typing import Any, Callable, Dict, Final, Mapping, Optional, Tuple, Union
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

from .agent_based_api.v1 import Metric, register, render, Result, State, Service

# TODO: Need to completely rework smart check. Use IDs instead of changing
# descriptions! But be careful: There is no standard neither for IDs nor for
# descriptions. Only use those, which are common sense.

Disk = Dict[str, Union[int, Tuple[int, int]]]

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

DISCOVERED_PARAMETERS: Final = (
    'Reallocated_Sector_Ct',
    'Spin_Retry_Count',
    'Reallocated_Event_Count',
    'Current_Pending_Sector',
    'Command_Timeout',
    'End-to-End_Error',
    'Reported_Uncorrect',
    'Uncorrectable_Error_Cnt',
    'UDMA_CRC_Error_Count',
    'CRC_Error_Count',
    #nvme
    'Critical_Warning',
)


def discover_smart_stats(section: Section) -> DiscoveryResult:
    for disk_name, disk in section.items():
        cleaned = {f: disk[f] for f in DISCOVERED_PARAMETERS if f in disk}
        if cleaned:
            yield Service(item=disk_name, parameters=cleaned)


OUTPUT_FIELDS: Tuple[Tuple[str, str, Callable], ...] = (
    ('Power_On_Hours', 'Powered on', lambda h: render.timespan(h * 3600)),
    ('Reported_Uncorrect', 'Uncorrectable errors', str),
    ('Uncorrectable_Error_Cnt', 'Uncorrectable errors', str),
    ('Power_Cycle_Count', 'Power cycles', str),
    ('Reallocated_Sector_Ct', 'Reallocated sectors', str),
    ('Reallocated_Event_Count', 'Reallocated events', str),
    ('Spin_Retry_Count', 'Spin retries', str),
    ('Current_Pending_Sector', 'Pending sectors', str),
    ('Command_Timeout', 'Command timeouts', str),
    ('End-to-End_Error', 'End-to-End errors', str),
    ('UDMA_CRC_Error_Count', 'UDMA CRC errors', str),
    ('CRC_Error_Count', 'UDMA CRC errors', str),
    #nvme
    ('Power_Cycles', 'Power cycles', str),
    ('Critical_Warning', 'Critical warning', str),
    ('Available_Spare', 'Available spare', render.percent),
    ('Percentage_Used', 'Percentage used', render.percent),
    ('Media_and_Data_Integrity_Errors', 'Media and data integrity errors', str),
    ('Error_Information_Log_Entries', 'Error information log entries', str),
    ('Data_Units_Read', 'Data units read', render.bytes),
    ('Data_Units_Written', 'Data units written', render.bytes),
)


def check_smart_stats(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    # params is a snapshot of all counters at the point of time of inventory
    disk = section.get(item)
    if disk is None:
        return

    for field, descr, renderer in OUTPUT_FIELDS:
        value = disk.get(field)
        if value is None:
            continue
        assert isinstance(value, int)

        infotext = "%s: %s" % (descr, renderer(value))

        if field == "Available_Spare":
            ref_value: Optional[int] = int(
                disk["Available_Spare_Threshold"])  # type: ignore[arg-type]
        else:
            ref_value = params.get(field)

        if ref_value is None:
            yield Result(state=State.OK, summary=infotext)
            yield Metric(field, value)
            continue

        if field == "Available_Spare":
            state = State.CRIT if value < ref_value else State.OK
        else:
            state = State.CRIT if value > ref_value else State.OK
        hints = [] if state == State.OK else ["during discovery: %d (!!)" % ref_value]

        # For reallocated event counts we experienced to many reported errors for disks
        # which still seem to be OK. The raw value increased by a small amount but the
        # aggregated value remained at it's initial/ok state. So we use the aggregated
        # value now. Only for this field.
        if field == "Reallocated_Event_Count":
            norm_value, norm_threshold = disk.get(  # type: ignore[misc]
                f"_normalized_{field}", (None, None))
            if norm_value is None:
                yield Result(state=State.OK, summary=infotext)
                yield Metric(field, value)
                continue
            hints.append("normalized value: %d" % norm_value)
            if norm_value <= norm_threshold:  # type: ignore[operator]
                state = State.CRIT
                hints[-1] += " (!!)"

        yield Result(
            state=state,
            summary=infotext + " (%s)" % ', '.join(hints) if hints else infotext,
        )
        yield Metric(field, value)


register.check_plugin(
    name="smart_stats",
    service_name="SMART %s Stats",
    discovery_function=discover_smart_stats,
    check_function=check_smart_stats,
    check_default_parameters={},  # needed to pass discovery parameters along!
)
