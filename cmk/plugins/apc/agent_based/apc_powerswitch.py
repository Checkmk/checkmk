#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
    startswith,
    State,
    StringTable,
)


@dataclass(frozen=True)
class APCPowerswitch:
    index: str
    name: str
    status: str


APCPowerswitchSection = Mapping[str, APCPowerswitch]


def parse_apc_powerswitch(string_table: Sequence[StringTable]) -> APCPowerswitchSection:
    if not string_table:
        return {}

    return {
        powerswitch[0]: APCPowerswitch(
            index=powerswitch[0],
            name=powerswitch[1],
            status=powerswitch[2],
        )
        for powerswitch in string_table[0]
    }


snmp_section_apc_powerswitch = SNMPSection(
    name="apc_powerswitch",
    parse_function=parse_apc_powerswitch,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.12.3.5.1.1",
            oids=[
                "1",
                "2",
                "4",
            ],
        )
    ],
    detect=startswith(
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.4.1.318.1.3.4",
    ),
)


def discover_apc_powerswitch(section: APCPowerswitchSection) -> DiscoveryResult:
    yield from (
        Service(
            item=powerswitch.index,
            parameters={"discovered_status": powerswitch.status},
        )
        for powerswitch in section.values()
        if powerswitch.status == "1"
    )


def check_apc_powerswitch(item: str, section: APCPowerswitchSection) -> CheckResult:
    state_mapping = {
        "1": (State.OK, "on"),
        "2": (State.WARN, "off"),
    }

    if (powerswitch := section.get(item)) is None:
        return

    state, state_readable = state_mapping.get(
        powerswitch.status,
        (
            State.UNKNOWN,
            f"unknown ({powerswitch.status})" if powerswitch.status else "unknown",
        ),
    )

    yield Result(state=state, summary=f"Port {powerswitch.name} has status {state_readable}")


check_plugin_apc_powerswitch = CheckPlugin(
    name="apc_powerswitch",
    service_name="Power Outlet Port %s",
    discovery_function=discover_apc_powerswitch,
    check_function=check_apc_powerswitch,
)
