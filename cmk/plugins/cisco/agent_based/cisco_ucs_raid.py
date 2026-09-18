#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# comNET GmbH, Fabian Binder - 2018-05-07

from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.cisco.lib_ucs import DETECT, MAP_OPERABILITY


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


def discover_cisco_ucs_raid(section: Section) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_cisco_ucs_raid(section: Section) -> CheckResult:
    yield Result(state=State(section.state), summary=f"Status: {section.operability}")
    yield Result(state=State.OK, summary=f"Model: {section.model}")
    yield Result(state=State.OK, summary=f"Vendor: {section.vendor}")
    yield Result(state=State.OK, summary=f"Serial number: {section.serial}")


snmp_section_cisco_ucs_raid = SimpleSNMPSection(
    name="cisco_ucs_raid",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.45.1.1",
        oids=["5", "7", "14", "17"],
    ),
    parse_function=parse_cisco_ucs_raid,
)

check_plugin_cisco_ucs_raid = CheckPlugin(
    name="cisco_ucs_raid",
    service_name="RAID Controller",
    discovery_function=discover_cisco_ucs_raid,
    check_function=check_cisco_ucs_raid,
)
