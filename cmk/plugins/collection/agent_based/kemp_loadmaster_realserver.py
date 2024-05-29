#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Final, NamedTuple

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
from cmk.plugins.lib.kemp_loadmaster import DETECT_KEMP_LOADMASTER, VSSection


class RealServer(NamedTuple):
    state: State
    state_txt: str
    id_virtual_service: str


RSSection = Mapping[str, Sequence[RealServer]]


_RS_STATE_MAP: Final = {
    "1": (State.OK, "in service"),
    "2": (State.CRIT, "out of service"),
    "3": (State.CRIT, "failed"),
    "4": (State.CRIT, "disabled"),
}


def parse_kemp_loadmaster_realserver(string_table: StringTable) -> RSSection:
    section = defaultdict(list)
    for id_virtual_service, ip_address, state in string_table:
        section[ip_address].append(
            RealServer(
                *_RS_STATE_MAP.get(state, (State.UNKNOWN, f"unknown[{state}]")),
                id_virtual_service,
            )
        )
    section.default_factory = None
    return section


snmp_section_kemp_loadmaster_realserver = SimpleSNMPSection(
    name="kemp_loadmaster_realserver",
    parse_function=parse_kemp_loadmaster_realserver,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12196.13.2.1",
        oids=[
            "1",  # ID of virtual Service B100-MIB::rSvsidx
            "2",  # IP address: B100-MIB::rSip
            "8",  # state: B100-MIB::rSstate
        ],
    ),
    detect=DETECT_KEMP_LOADMASTER,
)


def discover_kemp_loadmaster_realserver(
    section_kemp_loadmaster_realserver: RSSection | None,
    section_kemp_loadmaster_services: VSSection | None,
) -> DiscoveryResult:
    if section_kemp_loadmaster_realserver is None:
        return
    yield from (
        Service(item=item)
        for item, rservers in section_kemp_loadmaster_realserver.items()
        # If at least one of the virtual services are enabled, we want to
        # monitor it.
        if not all(rs.state_txt == "disabled" for rs in rservers)
    )


def check_kemp_loadmaster_realserver(
    item: str,
    section_kemp_loadmaster_realserver: RSSection | None,
    section_kemp_loadmaster_services: VSSection | None,
) -> CheckResult:
    rservers = (section_kemp_loadmaster_realserver or {}).get(item)
    if rservers is None:
        return

    vservices = (section_kemp_loadmaster_services or {}).values()
    for rs in rservers:
        summary = rs.state_txt.capitalize()
        for vservice in vservices:
            if rs.id_virtual_service == vservice.oid_end:
                summary = f"{vservice.name}: {summary}"
        yield Result(state=rs.state, summary=summary)


check_plugin_kemp_loadmaster_realserver = CheckPlugin(
    name="kemp_loadmaster_realserver",
    sections=["kemp_loadmaster_realserver", "kemp_loadmaster_services"],
    discovery_function=discover_kemp_loadmaster_realserver,
    check_function=check_kemp_loadmaster_realserver,
    service_name="Real Server %s",
)
