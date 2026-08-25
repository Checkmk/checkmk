#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.f5_bigip.lib import F5_BIGIP

# Agent / MIB output
# SysChassisPowerSupplyEntry ::=
#        SEQUENCE {
#                sysChassisPowerSupplyIndex                   INTEGER,
#                sysChassisPowerSupplyStatus                  INTEGER
#        }

# sysChassisPowerSupplyStatus
#   bad(0),
#   good(1),
#   notpresent(2)

_NOT_PRESENT = 2

_PSU_STATES = {
    0: (State.CRIT, "PSU state: bad!!"),
    1: (State.OK, "PSU state: good"),
    _NOT_PRESENT: (State.WARN, "PSU state: notpresent!"),
}

Section = Mapping[str, int]


def parse_f5_bigip_psu(string_table: StringTable) -> Section:
    return {psu: int(status) for psu, status in string_table}


def discover_f5_bigip_psu(section: Section) -> DiscoveryResult:
    # discover the PSU unless it's in state 2 (notpresent)
    yield from (Service(item=psu) for psu, status in section.items() if status != _NOT_PRESENT)


def check_f5_bigip_psu(item: str, section: Section) -> CheckResult:
    if (status := section.get(item)) is None:
        return

    state, summary = _PSU_STATES.get(status, (State.UNKNOWN, "PSU state is unknown"))
    yield Result(state=state, summary=summary)


snmp_section_f5_bigip_psu = SimpleSNMPSection(
    name="f5_bigip_psu",
    detect=F5_BIGIP,
    # Get ID and status from the SysChassisPowerSupplyTable
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.3.2.2.2.1",
        oids=[
            "1",  # F5-BIGIP-SYSTEM-MIB::sysChassisPowerSupplyIndex
            "2",  # F5-BIGIP-SYSTEM-MIB::sysChassisPowerSupplyStatus
        ],
    ),
    parse_function=parse_f5_bigip_psu,
)


check_plugin_f5_bigip_psu = CheckPlugin(
    name="f5_bigip_psu",
    service_name="PSU %s",
    discovery_function=discover_f5_bigip_psu,
    check_function=check_f5_bigip_psu,
)
