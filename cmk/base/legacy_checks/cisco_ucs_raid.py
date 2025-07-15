#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# comNET GmbH, Fabian Binder - 2018-05-07

from typing import NamedTuple

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cisco_ucs import DETECT, MAP_OPERABILITY

check_info = {}


class Section(NamedTuple):
    model: str
    state: int
    operability: str
    serial: str
    vendor: str


def parse_cisco_ucs_raid(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    return Section(
        string_table[0][0],
        *MAP_OPERABILITY[string_table[0][1]],
        string_table[0][2],
        string_table[0][3],
    )


def discover_cisco_ucs_raid(section):
    yield None, {}


def check_cisco_ucs_raid(_no_item, _no_params, section):
    yield section.state, f"Status: {section.operability}"
    yield 0, f"Model: {section.model}"
    yield 0, f"Vendor: {section.vendor}"
    yield 0, f"Serial number: {section.serial}"


check_info["cisco_ucs_raid"] = LegacyCheckDefinition(
    name="cisco_ucs_raid",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.45.1.1",
        oids=["5", "7", "14", "17"],
    ),
    parse_function=parse_cisco_ucs_raid,
    service_name="RAID Controller",
    discovery_function=discover_cisco_ucs_raid,
    check_function=check_cisco_ucs_raid,
)
