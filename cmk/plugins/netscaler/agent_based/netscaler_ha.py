#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

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

from .lib import SNMP_DETECT

_CURRENT_STATE_TO_HUMAN_READABLE_AND_MONITORING_STATE = {
    0: ("unknown", State.WARN),
    # 1 Indicates that the node is in the process of becoming part of the high
    #   availability configuration.
    1: ("initializing", State.WARN),
    2: ("down", State.CRIT),  # undocumented
    # 3 Indicates that the node is accessible and can function as either
    #   a primary or secondary node.
    3: ("functional", State.OK),
    # 4 Indicates that one of the high availability monitored interfaces
    #   has failed because of a card or link failure. # This state triggers a
    #   failover.
    4: ("some HA monitored interfaces failed", State.CRIT),
    5: ("monitorFail", State.WARN),  # undocumented
    6: ("monitorOK", State.WARN),  # undocumented
    # 7 Indicates that all the interfaces of the node are
    #   unusable because the interfaces on which high
    #   availability monitoring is enabled are not connected
    #   or are manually disabled. This state triggers a failover.
    7: ("all HA monitored interfaces failed", State.CRIT),
    # 8 Indicates that the node is in listening mode. It does not
    #   participate in high availability transitions or transfer
    #   configuration from the peer node. This is a configured
    #   value, not a statistic.
    8: ("configured to listening mode (dumb)", State.WARN),
    # 9 Indicates that the high availability status of the node has been
    #   manually disabled. Synchronization and propagation cannot take
    #   place between the peer nodes.
    9: ("HA status manually disabled", State.WARN),
    # 10 Indicates that the SSL card has failed. This state triggers a failover.
    10: ("SSL card failed", State.CRIT),
    # 11 Indicates that the route monitor has failed. This state triggers
    #    a failover.
    11: ("route monitor has failed", State.CRIT),
}

_PEER_STATE_TO_HUMAN_READABLE_AND_MONITORING_STATE = {
    0: ("standalone", State.OK),
    1: ("primary", State.OK),
    2: ("secondary", State.OK),
    3: ("unknown", State.WARN),
}


@dataclass(frozen=True, kw_only=True)
class Section:
    peer_state: int
    current_status: int
    current_state: int


def parse_netscaler_ha(string_table: StringTable) -> Section | None:
    return (
        Section(
            peer_state=int(string_table[0][0]),
            current_status=int(string_table[0][1]),
            current_state=int(string_table[0][2]),
        )
        if string_table
        else None
    )


snmp_section_netscaler_ha = SimpleSNMPSection(
    name="netscaler_ha",
    parse_function=parse_netscaler_ha,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.23",
        oids=[
            "3",
            "23",
            "24",
        ],
    ),
    detect=SNMP_DETECT,
)


def discover_netscaler_ha(section: Section) -> DiscoveryResult:
    yield Service()


def check_netscaler_ha(section: Section) -> CheckResult:
    if section.current_status == 0:
        yield Result(state=State.OK, summary="System not setup for HA")
        return

    self_description, self_state = _CURRENT_STATE_TO_HUMAN_READABLE_AND_MONITORING_STATE[
        section.current_state
    ]
    peer_description, peer_state = _PEER_STATE_TO_HUMAN_READABLE_AND_MONITORING_STATE[
        section.peer_state
    ]

    yield Result(state=self_state, summary=f"State: {self_description}")
    yield Result(state=peer_state, summary=f"Neighbor: {peer_description}")


check_plugin_netscaler_ha = CheckPlugin(
    name="netscaler_ha",
    service_name="HA Node Status",
    discovery_function=discover_netscaler_ha,
    check_function=check_netscaler_ha,
)
