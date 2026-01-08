#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD

route_type_mapping = {
    "DefaultRoute": "default route",
    "PBR": "policy based routing",
    "": "not defined",
}

route_state_mapping = {
    "UP": Result(state=State.OK, summary="Route is up"),
    "DOWN": Result(state=State.CRIT, summary="Route is down"),
    "UNDEF": Result(state=State.UNKNOWN, summary="Route is undefined"),
}


def discover_stormshield_route(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[5] == "UP":
            yield Service(item=line[0])


def check_stormshield_route(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            _index, typ, name, gateway_name, gateway_type, state = line
            yield route_state_mapping[state]
            infotext = f"Type: {route_type_mapping[typ]}, Router name: {name}, Gateway name: {gateway_name}, Gateway type: {gateway_type}"
            yield Result(state=State.OK, summary=infotext)


def parse_stormshield_route(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_stormshield_route = SimpleSNMPSection(
    name="stormshield_route",
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.14.1.1",
        oids=["1", "2", "4", "5", "7", "9"],
    ),
    parse_function=parse_stormshield_route,
)


check_plugin_stormshield_route = CheckPlugin(
    name="stormshield_route",
    service_name="Gateway %s",
    discovery_function=discover_stormshield_route,
    check_function=check_stormshield_route,
)
