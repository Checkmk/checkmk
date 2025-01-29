#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# check_mk plug-in to monitor Fujitsu storage systems supporting FJDARY-E60.MIB or FJDARY-E100.MIB
# Copyright (c) 2012 FuH Entwicklungsgesellschaft mbH, Umkirch, Germany. All rights reserved.
# Author: Philipp Hoefflin, 2012, hoefflin+cmk@fuh-e.de

from collections.abc import Mapping, MutableMapping, Sequence

# generic data structure widely used in the FJDARY-Mibs:
# <oid>
# <oid>.1: Index
# <oid>.3: Status
# the latter can be one of the following:
from typing import NamedTuple

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

FJDARYE_SUPPORTED_DEVICES = [
    ".1.3.6.1.4.1.211.1.21.1.60",  # fjdarye60
    ".1.3.6.1.4.1.211.1.21.1.100",  # fjdarye100
    ".1.3.6.1.4.1.211.1.21.1.101",  # fjdarye101
]

FJDARYE_RLUNS_STATUS_MAPPING = {
    "\x08": Result(state=State.WARN, summary="RLUN is rebuilding"),  # Back Space (decimal 8)
    "\x07": Result(state=State.WARN, summary="RLUN copyback in progress"),  # Bell (decimal 7)
    "A": Result(state=State.WARN, summary="RLUN spare is in use"),  # (decimal 65)
    "B": Result(
        state=State.OK,
        summary="RLUN is in RAID0 state",
    ),  # (decimal 66) - assumption that B is RAID0 state
    "\x00": Result(
        state=State.OK,
        summary="RLUN is in normal state",
    ),  # Null char (decimal 0) - assumption that \x00 is normal state
}


class FjdaryeRlun(NamedTuple):
    rlun_index: str
    raw_string: str


def parse_fjdarye_rluns(string_table: Sequence[StringTable]) -> Mapping[str, FjdaryeRlun]:
    readable_rluns: MutableMapping[str, FjdaryeRlun] = {}
    for rlun in string_table:
        for rlun_index, raw_string in rlun:
            readable_rluns[rlun_index] = FjdaryeRlun(rlun_index=rlun_index, raw_string=raw_string)

    return readable_rluns


snmp_section_fjdarye_rluns = SNMPSection(
    name="fjdarye_rluns",
    parse_function=parse_fjdarye_rluns,
    fetch=[
        SNMPTree(base=f"{device_oid}.3.4.2.1", oids=["1", "2"])
        for device_oid in FJDARYE_SUPPORTED_DEVICES
    ],
    detect=any_of(
        *[equals(".1.3.6.1.2.1.1.2.0", device_oid) for device_oid in FJDARYE_SUPPORTED_DEVICES]
    ),
)


def discover_fjdarye_rluns(section: Mapping[str, FjdaryeRlun]) -> DiscoveryResult:
    for rlun in section.values():
        if rlun.raw_string[3] == "\xa0":  # non-breaking space (decimal 160)
            # The fourth byte needs to be "\xa0" for a RLUN to be present
            yield Service(item=rlun.rlun_index)


def check_fjdarye_rluns(item: str, section: Mapping[str, FjdaryeRlun]) -> CheckResult:
    if (rlun := section.get(item)) is None:
        return

    if rlun.raw_string[3] != "\xa0":
        yield Result(state=State.CRIT, summary="RLUN is not present")
        return

    yield FJDARYE_RLUNS_STATUS_MAPPING.get(
        rlun.raw_string[2],  # The result state and summary are dependent on the third byte
        Result(state=State.CRIT, summary="RLUN in unknown state"),
    )


check_plugin_fjdarye_rluns = CheckPlugin(
    name="fjdarye_rluns",
    service_name="RLUN %s",
    discovery_function=discover_fjdarye_rluns,
    check_function=check_fjdarye_rluns,
)
