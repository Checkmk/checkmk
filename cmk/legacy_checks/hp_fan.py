#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

_STATUS_MAP: dict[str, tuple[State, str]] = {
    "0": (State.UNKNOWN, "unknown"),
    "1": (State.CRIT, "removed"),
    "2": (State.CRIT, "off"),
    "3": (State.WARN, "underspeed"),
    "4": (State.WARN, "overspeed"),
    "5": (State.OK, "ok"),
    "6": (State.UNKNOWN, "maxstate"),
}


def parse_hp_fan(string_table: StringTable) -> Mapping[str, str]:
    return {
        f"{tray_index}/{fan_index}": fan_state for fan_index, tray_index, fan_state in string_table
    }


def discover_hp_fan(section: Mapping[str, str]) -> DiscoveryResult:
    yield from (Service(item=fan) for fan in section)


def check_hp_fan(item: str, section: Mapping[str, str]) -> CheckResult:
    if (raw := section.get(item)) is None:
        return
    state, status_txt = _STATUS_MAP[raw]
    yield Result(state=state, summary=status_txt)


snmp_section_hp_fan = SimpleSNMPSection(
    name="hp_fan",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "hp"),
        any_of(
            contains(".1.3.6.1.2.1.1.1.0", "5406rzl2"), contains(".1.3.6.1.2.1.1.1.0", "5412rzl2")
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.54.2.1.1",
        oids=[OIDEnd(), "2", "4"],
    ),
    parse_function=parse_hp_fan,
)


check_plugin_hp_fan = CheckPlugin(
    name="hp_fan",
    service_name="Fan %s",
    discovery_function=discover_hp_fan,
    check_function=check_hp_fan,
)
