#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# APC NetShelter Advanced Rack PDU (APDU series) - Outlet status monitoring
# MIB reference: mibs/APC-CPDU-v1_9-MIB.txt
#
# .1.3.6.1.4.1.318.1.1.32.5.5.1.2  1           - outlet index
# .1.3.6.1.4.1.318.1.1.32.5.5.1.3  "OUTLET 1"  - outlet name
# .1.3.6.1.4.1.318.1.1.32.5.5.1.4  2           - outlet status (1=off, 2=on)

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based.apc_netshelterpdu_power import (
    DETECT_APC_NETSHELTERPDU,
)


@dataclass(frozen=True, kw_only=True)
class APCNetShelterOutlet:
    index: str
    name: str
    status: str


type APCNetShelterOutletSection = Mapping[str, APCNetShelterOutlet]


def parse_apc_netshelterpdu_outlet(
    string_table: Sequence[StringTable],
) -> APCNetShelterOutletSection:
    return {
        outlet[0]: APCNetShelterOutlet(
            index=outlet[0],
            name=outlet[1],
            status=outlet[2],
        )
        for outlet in string_table[0]
    }


snmp_section_apc_netshelterpdu_outlet = SNMPSection(
    name="apc_netshelterpdu_outlet",
    parse_function=parse_apc_netshelterpdu_outlet,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.5.5.1",
            oids=[
                "2",  # outlet index
                "3",  # outlet name
                "4",  # outlet status (1=off, 2=on)
            ],
        )
    ],
    detect=DETECT_APC_NETSHELTERPDU,
)


def discover_apc_netshelterpdu_outlet(
    section: APCNetShelterOutletSection,
) -> DiscoveryResult:
    yield from (Service(item=outlet.index) for outlet in section.values() if outlet.status == "2")


def check_apc_netshelterpdu_outlet(item: str, section: APCNetShelterOutletSection) -> CheckResult:
    state_mapping = {
        "2": (State.OK, "on"),
        "1": (State.WARN, "off"),
    }

    if (outlet := section.get(item)) is None:
        return

    state, state_readable = state_mapping.get(
        outlet.status,
        (
            State.UNKNOWN,
            f"unknown ({outlet.status})" if outlet.status else "unknown",
        ),
    )

    yield Result(state=state, summary=f"{outlet.name}: {state_readable}")


check_plugin_apc_netshelterpdu_outlet = CheckPlugin(
    name="apc_netshelterpdu_outlet",
    service_name="Power Outlet Port %s",
    discovery_function=discover_apc_netshelterpdu_outlet,
    check_function=check_apc_netshelterpdu_outlet,
)
