#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    any_of,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.kemp_loadmaster.lib import DETECT_KEMP_LOADMASTER, VirtualService
from cmk.plugins.kemp_loadmaster.lib import VSSection as Section

class VirtualService(NamedTuple):
    name: str
    connections: Optional[int]
    state: State
    state_txt: str
    oid_end: str


ServiceSection = Mapping[str, VirtualService]
HaSection = Sequence[Sequence]
ClusterServiceSection = Mapping[str, Optional[ServiceSection]]
ClusterHaSection = Mapping[str, Optional[HaSection]]

DETECT_KEMP_LOADMASTER = any_of(
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12196.250.10"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2021.250.10"),
)

_VS_STATE_MAP: Final = {
    "1": (State.OK, "in service"),
    "2": (State.CRIT, "out of service"),
    "3": (State.CRIT, "failed"),
    "4": (State.WARN, "disabled"),
    "5": (State.WARN, "sorry"),
    "6": (State.OK, "redirect"),
    "7": (State.CRIT, "error message"),
}


def parse_kemp_loadmaster_services(string_table: StringTable) -> Section:
    return {
        name: VirtualService(
            name,
            int(conns) if conns.isdigit() else None,
            *_VS_STATE_MAP.get(state, (State.UNKNOWN, f"unknown[{state}]")),
            oid_end,
        )
        for name, state, conns, oid_end in string_table
        if name != ""
    }


snmp_section_kemp_loadmaster_services = SimpleSNMPSection(
    name="kemp_loadmaster_services",
    parse_function=parse_kemp_loadmaster_services,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12196.13.1.1",
        oids=[
            "13",  # B100-MIB::vSname
            "14",  # B100-MIB::vSstate
            "21",  # B100-MIB::conns
            OIDEnd(),
        ],
    ),
    detect=DETECT_KEMP_LOADMASTER,
)


def discover_kemp_loadmaster_services(section: Section) -> DiscoveryResult:
    for name, virtual_service in section.items():
        if virtual_service.state_txt not in ["disabled", "unknown[]"]:
            yield Service(item=name)


def check_kemp_loadmaster_services(item: str, section: Section) -> CheckResult:
    virtual_service = section.get(item)
    if virtual_service is None:
        return
    yield Result(state=virtual_service.state, summary=f"Status: {virtual_service.state_txt}")
    if virtual_service.connections is not None:
        yield Result(state=State.OK, summary=f"Active connections: {virtual_service.connections}")
        yield Metric("conns", virtual_service.connections)

def cluster_check_kemp_loadmaster_services(item: str,
                                           section_kemp_loadmaster_services: ClusterServiceSection,
                                           section_kemp_loadmaster_ha: ClusterHaSection) -> CheckResult:
    """Check state of a pair of Kemp load masters in HA mode. This check does not support Clusters,
    with 4 and more nodes. The better of both states is reported.
    """

    if len(section_kemp_loadmaster_services) != 2:
        yield from _unsupported_node_count(section_kemp_loadmaster_services)
        return

    host = _get_primary_node(section_kemp_loadmaster_ha)

    if host is not None:
        yield Result(state=State.OK, summary=f"Active node: {host}")
        yield from check_kemp_loadmaster_services(item, section_kemp_loadmaster_services[host], section_kemp_loadmaster_ha)


def _get_primary_node(section_kemp_loadmaster_ha: ClusterServiceSection) -> Optional[str]:
    host_selector: Optional[str] = None

    for host, ha in section_kemp_loadmaster_ha.items():
        if ha[0][0] == '1':
            host_selector = host
            break

    return host_selector

def _unsupported_node_count(section: ClusterServiceSection):
    yield Result(
        state=State.UNKNOWN,
        summary=f'Cluster check for this service only supports one pair of Loadbalancers in HA-Mode. Got {len(section)} '
                f'{"node" if len(section) == 1 else "nodes"}'
    )

check_plugin_kemp_loadmaster_services = CheckPlugin(
    name="kemp_loadmaster_services",
    service_name="Service %s",
    check_function=check_kemp_loadmaster_services,
    discovery_function=discover_kemp_loadmaster_services,
)
