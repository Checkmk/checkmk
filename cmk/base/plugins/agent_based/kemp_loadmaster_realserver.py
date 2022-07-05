#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from typing import Final, Mapping, NamedTuple, Sequence

from .agent_based_api.v1 import any_of, equals, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class RealServer(NamedTuple):
    state: State
    state_txt: str


Section = Mapping[str, Sequence[RealServer]]


_RS_STATE_MAP: Final = {
    "1": (State.OK, "in service"),
    "2": (State.CRIT, "out of service"),
    "3": (State.CRIT, "failed"),
    "4": (State.CRIT, "disabled"),
}


def parse_kemp_loadmaster_realserver(string_table: StringTable) -> Section:
    section = defaultdict(list)
    for server, state in string_table:
        section[server].append(
            RealServer(*_RS_STATE_MAP.get(state, (State.UNKNOWN, f"unknown[{state}]")))
        )
    section.default_factory = None
    return section


register.snmp_section(
    name="kemp_loadmaster_realserver",
    parse_function=parse_kemp_loadmaster_realserver,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12196.13.2.1",
        oids=[
            "2",  # IP address: B100-MIB::rSip
            "8",  # state: B100-MIB::rSstate
        ],
    ),
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12196.250.10"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2021.250.10"),
    ),
)


def discover_kemp_loadmaster_realserver(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, rservers in section.items()
        # If at least one of the virtual services are enabled, we want to
        # monitor it.
        if not all(rs.state_txt == "disabled" for rs in rservers)
    )


def check_kemp_loadmaster_realserver(item: str, section: Section) -> CheckResult:
    rservers = section.get(item)
    if rservers is None:
        return

    yield from (Result(state=rs.state, summary=rs.state_txt.capitalize()) for rs in rservers)


register.check_plugin(
    name="kemp_loadmaster_realserver",
    discovery_function=discover_kemp_loadmaster_realserver,
    check_function=check_kemp_loadmaster_realserver,
    service_name="Real Server %s",
)
