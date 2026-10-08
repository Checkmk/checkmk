#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def discover_dell_idrac_power(section: Sequence[StringTable]) -> DiscoveryResult:
    for index, _status, _count in section[0]:
        yield Service(item=index)


SHORT_NAME_PATTERN = re.compile(r"(?i)^idrac(\d+)")
TRANSLATE_STATUS_V4 = {
    "0": (State.OK, "not redundant"),
    "1": (State.OK, "full"),
    "2": (State.CRIT, "lost"),
}
TRANSLATE_STATUS_V3 = {
    "1": (State.UNKNOWN, "other"),
    "2": (State.UNKNOWN, "unknown"),
    "3": (State.OK, "full"),
    "4": (State.WARN, "degraded"),
    "5": (State.CRIT, "lost"),
    "6": (State.OK, "not redundant"),
    "7": (State.WARN, "redundancy offline"),
}
MIB_V4 = "iDRAC10 or newer"
MIB_V3 = "iDRAC9 or older"

# RacTypeEnum gives every iDRAC generation a block of 16 values: iDRAC7 starts at 16, iDRAC8 at
# 32, iDRAC9 at 48 and continues at 64 and 80 for the 15th and 16th server generation, iDRAC10
# starts at 96. Below 16 only other(1) and unknown(2) are defined, neither of which names a
# generation.
RAC_TYPE_IDRAC7 = 16
RAC_TYPE_IDRAC10 = 96


def _get_translate_status(
    rac_type: str, short_name: str
) -> tuple[Mapping[str, tuple[State, str]], str]:
    """
    Get the version dependent powerUnitRedundancyStatus table and the name of its MIB.

    With iDRAC10 v4 of the MIB was introduced, all other still supported generations use v3.
    racType names the generation even on devices whose racShortName does not, so it is asked
    first.
    """
    try:
        rac_type_value = int(rac_type)
    except ValueError:
        pass
    else:
        if rac_type_value >= RAC_TYPE_IDRAC10:
            return TRANSLATE_STATUS_V4, MIB_V4
        if rac_type_value >= RAC_TYPE_IDRAC7:
            return TRANSLATE_STATUS_V3, MIB_V3

    if (match := SHORT_NAME_PATTERN.match(short_name)) is not None and int(match.group(1)) < 10:
        return TRANSLATE_STATUS_V3, MIB_V3

    return TRANSLATE_STATUS_V4, MIB_V4


# A column the device does not answer for a row is padded with an empty string, and a row exists
# as soon as any column answers. An empty value therefore means the device reported nothing.
NOT_REPORTED = "Status: not reported by the device"


def check_dell_idrac_power(item: str, section: Sequence[StringTable]) -> CheckResult:
    def _rac_info(column: int) -> str:
        """Read one of the racInfoGroup scalars, which the device may leave unanswered."""
        try:
            return section[2][0][column]
        except IndexError:
            return ""

    translate_status, mib = _get_translate_status(rac_type=_rac_info(1), short_name=_rac_info(0))

    for index, status, _count in section[0]:
        if index == item:
            if not status:
                yield Result(state=State.UNKNOWN, summary=NOT_REPORTED)
                return
            # A value the detected MIB does not define. Naming it together with the MIB makes a
            # wrong detection visible.
            state, state_readable = translate_status.get(
                status, (State.UNKNOWN, f"undefined value {status} (assuming the MIB for {mib})")
            )
            yield Result(state=state, summary="Status: %s" % state_readable)


def parse_dell_idrac_power(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_dell_idrac_power = SNMPSection(
    name="dell_idrac_power",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.5"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.4.600.10.1",
            oids=["2", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.4.600.12.1",
            oids=["2", "5", "7", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.1.1",
            oids=[
                "2",  # IDRAC-MIB::racShortName
                "7",  # IDRAC-MIB::racType
            ],
        ),
    ],
    parse_function=parse_dell_idrac_power,
)


check_plugin_dell_idrac_power = CheckPlugin(
    name="dell_idrac_power",
    service_name="Power Supply Redundancy %s",
    discovery_function=discover_dell_idrac_power,
    check_function=check_dell_idrac_power,
)


def discover_dell_idrac_power_unit(section: Sequence[StringTable]) -> DiscoveryResult:
    for index, _status, _psu_type, _location in section[1]:
        yield Service(item=index)


def check_dell_idrac_power_unit(item: str, section: Sequence[StringTable]) -> CheckResult:
    translate_status = {
        "1": (State.UNKNOWN, "OTHER"),
        "2": (State.UNKNOWN, "UNKNOWN"),
        "3": (State.OK, "OK"),
        "4": (State.WARN, "NONCRITICAL"),
        "5": (State.CRIT, "CRITICAL"),
        "6": (State.CRIT, "NONRECOVERABLE"),
    }

    translate_type = {
        "1": "OTHER",
        "2": "UNKNOWN",
        "3": "LINEAR",
        "4": "SWITCHING",
        "5": "BATTERY",
        "6": "UPS",
        "7": "CONVERTER",
        "8": "REGULATOR",
        "9": "AC",
        "10": "DC",
        "11": "VRM",
    }

    for index, status, psu_type, location in section[1]:
        if index == item:
            if not status:
                yield Result(state=State.UNKNOWN, summary=NOT_REPORTED)
                return
            state, state_readable = translate_status[status]
            summary = [f"Status: {state_readable}"]
            if psu_type:
                summary.append(f"Type: {translate_type[psu_type]}")
            if location:
                summary.append(f"Name: {location}")
            yield Result(state=state, summary=", ".join(summary))
            return


check_plugin_dell_idrac_power_unit = CheckPlugin(
    name="dell_idrac_power_unit",
    service_name="Power Supply %s",
    sections=["dell_idrac_power"],
    discovery_function=discover_dell_idrac_power_unit,
    check_function=check_dell_idrac_power_unit,
)
