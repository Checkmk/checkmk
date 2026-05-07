#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# check_mk plug-in to monitor Fujitsu storage systems supporting FJDARY-E60.MIB or FJDARY-E100.MIB
# Copyright (c) 2012 FuH Entwicklungsgesellschaft mbH, Umkirch, Germany. All rights reserved.
# Author: Philipp Hoefflin, 2012, hoefflin+cmk@fuh-e.de
# generic data structure widely used in the FJDARY-Mibs:
# <oid>
# <oid>.1: Index
# <oid>.3: Status

from collections.abc import Sequence
from typing import NewType

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
    ".1.3.6.1.4.1.211.1.21.1.150",  # fjdarye500
    ".1.3.6.1.4.1.211.1.21.1.153",  # fjdarye600
]


FJDARYE_SUM_STATUS = {
    "1": Result(state=State.CRIT, summary="Status: unknown"),
    "2": Result(state=State.CRIT, summary="Status: unused"),
    "3": Result(state=State.OK, summary="Status: ok"),
    "4": Result(state=State.WARN, summary="Status: warning"),
    "5": Result(state=State.CRIT, summary="Status: failed"),
}

FjdaryeDeviceStatus = NewType("FjdaryeDeviceStatus", str)


def parse_fjdarye_sum(string_table: Sequence[StringTable]) -> FjdaryeDeviceStatus | None:
    for row in string_table:
        for status in row:
            if len(status) == 1:
                return FjdaryeDeviceStatus(status[0])

    return None


snmp_section_fjdarye_summary_status = SNMPSection(
    name="fjdarye_summary_status",
    parse_function=parse_fjdarye_sum,
    fetch=[
        SNMPTree(base=f"{device_oid}.6", oids=["0"]) for device_oid in FJDARYE_SUPPORTED_DEVICES
    ],
    detect=any_of(
        *[equals(".1.3.6.1.2.1.1.2.0", device_oid) for device_oid in FJDARYE_SUPPORTED_DEVICES]
    ),
)


def discover_fjdarye_sum(section: FjdaryeDeviceStatus | None) -> DiscoveryResult:
    if section:
        yield Service()


def check_fjdarye_sum(section: FjdaryeDeviceStatus | None) -> CheckResult:
    if section is not None:
        yield FJDARYE_SUM_STATUS.get(
            section, Result(state=State.UNKNOWN, summary="Status: unknown")
        )


check_plugin_fjdarye_summary_status = CheckPlugin(
    name="fjdarye_summary_status",
    service_name="Summary Status",
    discovery_function=discover_fjdarye_sum,
    check_function=check_fjdarye_sum,
)
