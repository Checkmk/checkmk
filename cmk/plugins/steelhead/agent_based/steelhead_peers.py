#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.17163.1.1.2.6.1.1.2.1 vadetsh1 --> STEELHEAD-MIB::peerHostname.1
# .1.3.6.1.4.1.17163.1.1.2.6.1.1.3.1 8.5.3c --> STEELHEAD-MIB::peerVersion.1
# .1.3.6.1.4.1.17163.1.1.2.6.1.1.4.1 10.1.0.14 --> STEELHEAD-MIB::peerAddress.1
# .1.3.6.1.4.1.17163.1.1.2.6.1.1.5.1 CX770 --> STEELHEAD-MIB::peerModel.1


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
from cmk.plugins.steelhead.lib import DETECT_STEELHEAD


def parse_steelhead_peers(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_steelhead_peers = SimpleSNMPSection(
    name="steelhead_peers",
    parse_function=parse_steelhead_peers,
    detect=DETECT_STEELHEAD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.17163.1.1.2.6.1.1",
        oids=["2", "3", "4", "5"],
    ),
)


def discover_steelhead_peers(section: StringTable) -> DiscoveryResult:
    yield from (
        Service(item=host)
        for host, _version, _client, client_type in section
        if client_type != "Steelhead Mobile"
    )


def check_steelhead_peers(item: str, section: StringTable) -> CheckResult:
    for host, version, client, client_type in section:
        if host == item:
            yield Result(
                state=State.OK,
                summary=f"Version: {version}, Client Address: {client} ({client_type})",
            )
            return
    yield Result(state=State.CRIT, summary="Peer not connected")


check_plugin_steelhead_peers = CheckPlugin(
    name="steelhead_peers",
    service_name="Peer %s",
    discovery_function=discover_steelhead_peers,
    check_function=check_steelhead_peers,
)
