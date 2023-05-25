#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# EXAMPLE DATA FROM: WDC SSC-D0128SC-2100
# <<<smart>>>
# /dev/sda ATA WDC_SSC-D0128SC-   1 Raw_Read_Error_Rate     0x000b   100   100   050    Pre-fail  Always       -       16777215
# /dev/sda ATA WDC_SSC-D0128SC-   3 Spin_Up_Time            0x0007   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   5 Reallocated_Sector_Ct   0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   7 Seek_Error_Rate         0x000b   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       1408
# /dev/sda ATA WDC_SSC-D0128SC-  10 Spin_Retry_Count        0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-  12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       523
# /dev/sda ATA WDC_SSC-D0128SC- 168 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1
# /dev/sda ATA WDC_SSC-D0128SC- 175 Program_Fail_Count_Chip 0x0003   100   100   010    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 192 Power-Off_Retract_Count 0x0012   100   100   000    Old_age   Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 194 Temperature_Celsius     0x0022   040   100   000    Old_age   Always       -       40 (Lifetime Min/Max 30/60)
# /dev/sda ATA WDC_SSC-D0128SC- 197 Current_Pending_Sector  0x0012   100   100   000    Old_age   Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 240 Head_Flying_Hours       0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 170 Unknown_Attribute       0x0003   100   100   010    Pre-fail  Always       -       1769478
# /dev/sda ATA WDC_SSC-D0128SC- 173 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       4217788040605
import time
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from typing import Any, Final, Tuple

from .agent_based_api.v1 import (
    get_rate,
    get_value_store,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Mapping[str, Mapping[str, int]]

Disk = MutableMapping[str, int]
Disks = MutableMapping[str, Disk]

# The command timeouts is a counter and we experienced that on some devices, it will already be
# increased by one count after a simple reboot. In a faulty situation it will however increase in
# much larger steps (100 or 1000). So we accept any rate below 100 counts per hour.
# See CMK-7684
MAX_COMMAND_TIMEOUTS_PER_HOUR = 100

CRC_ERRORS_ID: Final = 199

# This mapping also limits the used ATA attributes.
# All ATA attributes not listed here will be discarded when parsing the raw agent section
ATA_ID_TO_ATTRIBUTE_NAME: Final[Mapping[int, str]] = {
    5: "Reallocated_Sector_Ct",
    9: "Power_On_Hours",
    10: "Spin_Retry_Count",
    12: "Power_Cycle_Count",
    184: "End-to-End_Error",
    187: "Reported_Uncorrect",
    188: "Command_Timeout",
    194: "Temperature",
    196: "Reallocated_Event_Count",
    197: "Current_Pending_Sector",
    CRC_ERRORS_ID: "CRC_Error_Count",
}


def _set_int_or_zero(disk: Disk, key: str, value: Any) -> None:
    try:
        disk[key] = int(value)
    except ValueError:
        disk[key] = 0


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
                  'Temperature': 40}}

    """
    ata_lines = (line for line in string_table if len(line) >= 13)
    nvme_lines = (line for line in string_table if 3 <= len(line) <= 6)

    return {**_parse_ata_lines(ata_lines), **_parse_nvme_lines(nvme_lines)}


def _parse_ata_lines(ata_lines: Iterable[Sequence[str]]) -> Section:
    ata_disks: MutableMapping[str, Disk] = {}

    for (
        disk_path,
        _disk_type,
        _disk_name,
        ID,
        attribute_name,
        _flag,
        value,
        _worst,
        threshold,
        _type,
        _updated,
        _when_failed,
        raw_value,
        *_raw_value_info,
    ) in ata_lines:
        disk = ata_disks.setdefault(disk_path, {})

        if attribute_name == "Unknown_Attribute":
            continue

        if int(ID) == CRC_ERRORS_ID and attribute_name == "UDMA_CRC_Error_Count":
            # UDMA_CRC_Error_Count and CRC_Error_Count share the same attribute ID (199).
            # Since we explicitly distinguish between the two, we choose "UDMA_CRC_Error_Count"
            # whenever the ID 199 comes with this textual information.
            # Otherwise, we default to CRC_Error_Count.
            _set_int_or_zero(disk, attribute_name, raw_value)
            continue

        if (lookup_attribute_name := ATA_ID_TO_ATTRIBUTE_NAME.get(int(ID))) is None:
            if attribute_name in disk:
                # Don't override already set attributes
                continue
            _set_int_or_zero(disk, attribute_name, raw_value)
            continue

        _set_int_or_zero(disk, lookup_attribute_name, raw_value)

        if lookup_attribute_name == "Reallocated_Event_Count":  # special case, see check function
            try:
                disk["_normalized_value_Reallocated_Event_Count"] = int(value)
                disk["_normalized_threshold_Reallocated_Event_Count"] = int(threshold)
            except ValueError:
                pass

    return ata_disks


def _parse_nvme_lines(nvme_lines: Iterable[Sequence[str]]) -> Section:
    nvme_disks: MutableMapping[str, Disk] = {}

    for line in nvme_lines:
        if "/dev" in line[0]:
            disk = nvme_disks.setdefault(line[0], {})
            continue

        field, value = [e.strip() for e in " ".join(line).split(":")]
        key = field.replace(" ", "_")
        value = value.replace("%", "").replace(".", "").replace(",", "")
        if field == "Temperature":
            _set_int_or_zero(disk, key, value.split()[0])
        elif field == "Critical Warning":
            disk[key] = int(value, 16)
        elif field == "Data Units Read":
            disk[key] = int(value.split()[0]) * 512000
        elif field == "Data Units Written":
            disk[key] = int(value.split()[0]) * 512000
        else:
            _set_int_or_zero(disk, key, value)

    return nvme_disks


register.agent_section(
    name="smart",
    parse_function=parse_raw_values,
)

DISCOVERED_PARAMETERS: Final = (
    "Reallocated_Sector_Ct",  # 5
    "Spin_Retry_Count",  # 10
    "Reallocated_Event_Count",  # 196
    "Current_Pending_Sector",  # 197
    "Command_Timeout",  # 188
    "End-to-End_Error",  # 184
    "Reported_Uncorrect",  # 187
    "UDMA_CRC_Error_Count",  # 199
    # nvme
    "Critical_Warning",
    "Media_and_Data_Integrity_Errors",
)


def discover_smart_stats(section: Section) -> DiscoveryResult:
    for disk_name, disk in section.items():
        cleaned = {f: disk[f] for f in DISCOVERED_PARAMETERS if f in disk}
        if cleaned:
            yield Service(item=disk_name, parameters=cleaned)


# currently unused, until we agree on which output is only
# needed in the details. Then use it in place of "_summary"
# in the OUTPUT_FIELDS data structure.
def _notice(state: State, text: str) -> Result:
    return Result(state=state, notice=text)


def _summary(state: State, text: str) -> Result:
    return Result(state=state, summary=text)


OUTPUT_FIELDS: Tuple[Tuple[Callable[[State, str], Result], str, str, Callable], ...] = (
    # ATA
    (_summary, "Power_On_Hours", "Powered on", lambda h: render.timespan(h * 3600)),  # 9, also nvme
    (_summary, "Power_Cycle_Count", "Power cycles", str),  # 12
    (_summary, "Reported_Uncorrect", "Uncorrectable errors", str),  # 187
    (_summary, "Reallocated_Sector_Ct", "Reallocated sectors", str),  # 5
    (_summary, "Reallocated_Event_Count", "Reallocated events", str),  # 196
    (_summary, "Spin_Retry_Count", "Spin retries", str),  # 10
    (_summary, "Current_Pending_Sector", "Pending sectors", str),  # 197
    (_summary, "Command_Timeout", "Command timeout counter", str),  # 188
    (_summary, "End-to-End_Error", "End-to-End errors", str),  # 184
    (_summary, "UDMA_CRC_Error_Count", "UDMA CRC errors", str),  # 199
    (_summary, "CRC_Error_Count", "CRC errors", str),  # also 199
    # nvme
    (_summary, "Power_Cycles", "Power cycles", str),
    (_summary, "Critical_Warning", "Critical warning", str),
    (_summary, "Available_Spare", "Available spare", render.percent),
    (_summary, "Percentage_Used", "Percentage used", render.percent),
    (_summary, "Media_and_Data_Integrity_Errors", "Media and data integrity errors", str),
    (_summary, "Error_Information_Log_Entries", "Error information log entries", str),
    (_summary, "Data_Units_Read", "Data units read", render.bytes),
    (_summary, "Data_Units_Written", "Data units written", render.bytes),
)


def check_smart_stats(item: str, params: Mapping[str, int], section: Section) -> CheckResult:
    # params is a snapshot of all counters at the point of time of inventory
    disk = section.get(item)
    if disk is None:
        return

    for make_result, field, descr, renderer in OUTPUT_FIELDS:
        value = disk.get(field)
        if value is None:
            continue
        assert isinstance(value, int)

        infotext = "%s: %s" % (descr, renderer(value))

        ref_value = params.get(field)
        if field == "Available_Spare":
            ref_value = disk["Available_Spare_Threshold"]

        if ref_value is None:
            yield make_result(State.OK, infotext)
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
            try:
                norm_value = disk[f"_normalized_value_{field}"]
                norm_threshold = disk[f"_normalized_threshold_{field}"]
            except KeyError:
                yield make_result(State.OK, infotext)
                yield Metric(field, value)
                continue
            hints.append("normalized value: %d" % norm_value)
            if norm_value <= norm_threshold:
                state = State.CRIT
                hints[-1] += " (!!)"

        if field == "Command_Timeout":
            rate = get_rate(get_value_store(), "cmd_timeout", time.time(), value)
            state = State.OK if rate < MAX_COMMAND_TIMEOUTS_PER_HOUR / (60 * 60) else State.CRIT
            hints = (
                []
                if state == State.OK
                else [
                    f"counter increased more than {MAX_COMMAND_TIMEOUTS_PER_HOUR} counts / h (!!). "
                    f"Value during discovery was: {ref_value}"
                ]
            )

        yield make_result(state, infotext + " (%s)" % ", ".join(hints) if hints else infotext)
        yield Metric(field, value)


register.check_plugin(
    name="smart_stats",
    sections=["smart"],
    service_name="SMART %s Stats",
    discovery_function=discover_smart_stats,
    check_function=check_smart_stats,
    check_default_parameters={},  # needed to pass discovery parameters along!
)
