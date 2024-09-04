#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
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

from .detection import DETECT_BLADE

# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.2.1 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.2.2 2
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.2.3 3
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.2.4 4
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.2.5 5
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.3.1 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.3.2 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.3.3 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.3.4 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.3.5 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.4.1 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.4.2 3
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.4.3 255
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.4.4 0
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.4.5 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.5.1 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.5.2 12
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.5.3 9
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.5.4 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.5.5 1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.6.1 ESX1
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.6.2 ESX109
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.6.3 ESX110
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.6.4 ESX137
# .1.3.6.1.4.1.2.3.51.2.22.1.5.1.1.6.5 ESX138


@dataclass
class Blade:
    exists: str
    power: str
    health: str
    name: str


Section = Mapping[str, Blade]


def parse_blade_blades(string_table: StringTable) -> Section:
    return {item: Blade(*rest) for item, *rest in string_table}


snmp_section_blade_blades = SimpleSNMPSection(
    name="blade_blades",
    detect=DETECT_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.22.1.5.1.1",
        oids=["2", "3", "4", "5", "6"],
    ),
    parse_function=parse_blade_blades,
)


def inventory_blade_blades(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, blade in section.items() if blade.power == "1")


MAP_EXISTS = {
    "0": (State.CRIT, "false"),
    "1": (State.OK, "true"),
}

MAP_POWER = {
    "0": (State.CRIT, "off"),
    "1": (State.OK, "on"),
    "3": (State.WARN, "standby"),
    "4": (State.WARN, "hibernate"),
    "255": (State.UNKNOWN, "unknown"),
}

MAP_HEALTH = {
    "0": (State.UNKNOWN, "unknown"),
    "1": (State.OK, "good"),
    "2": (State.WARN, "warning"),
    "3": (State.CRIT, "critical"),
    "4": (State.WARN, "kernel mode"),
    "5": (State.OK, "discovering"),
    "6": (State.CRIT, "communications error"),
    "7": (State.CRIT, "no power"),
    "8": (State.WARN, "flashing"),
    "9": (State.CRIT, "initialization Failure"),
    "10": (State.CRIT, "insuffiecient power"),
    "11": (State.CRIT, "power denied"),
    "12": (State.WARN, "maintenance mode"),
    "13": (State.WARN, "firehose dump"),
}


def check_blade_blades(item: str, section: Section) -> CheckResult:
    if (blade := section.get(item)) is None:
        return

    yield Result(state=State.OK, summary=blade.name)
    state, state_readable = MAP_EXISTS[blade.exists]
    yield Result(state=state, summary="Exists: %s" % state_readable)
    state, state_readable = MAP_POWER[blade.power]
    yield Result(state=state, summary="Power: %s" % state_readable)
    state, state_readable = MAP_HEALTH[blade.health]
    yield Result(state=state, summary="Health: %s" % state_readable)


check_plugin_blade_blades = CheckPlugin(
    name="blade_blades",
    service_name="Blade %s",
    discovery_function=inventory_blade_blades,
    check_function=check_blade_blades,
)
