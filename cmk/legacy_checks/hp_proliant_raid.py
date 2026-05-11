#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.hp_proliant.lib import DETECT, sanitize_item


class HpProRaid(NamedTuple):
    name: str
    status: str
    size_bytes: int
    rebuild_percent: int


_MAP_STATES = {
    "1": (State.UNKNOWN, "other"),
    "2": (State.OK, "OK"),
    "3": (State.CRIT, "failed"),
    "4": (State.WARN, "unconfigured"),
    "5": (State.WARN, "recovering"),
    "6": (State.WARN, "ready for rebuild"),
    "7": (State.WARN, "rebuilding"),
    "8": (State.CRIT, "wrong drive"),
    "9": (State.CRIT, "bad connect"),
    "10": (State.CRIT, "overheating"),
    "11": (State.WARN, "shutdown"),
    "12": (State.WARN, "automatic data expansion"),
    "13": (State.CRIT, "not available"),
    "14": (State.WARN, "queued for expansion"),
    "15": (State.WARN, "multi-path access degraded"),
    "16": (State.WARN, "erasing"),
}


def parse_hp_proliant_raid(string_table: StringTable) -> dict[str, HpProRaid]:
    parsed: dict[str, HpProRaid] = {}
    for number, name, status, size_str, rebuild in string_table:
        itemname = sanitize_item(f"{name} {number}".strip())
        parsed.setdefault(
            itemname,
            HpProRaid(
                name=itemname,
                status=status,
                size_bytes=int(size_str) * 1024 * 1024,
                rebuild_percent=int(rebuild),
            ),
        )

    return parsed


def discover_hp_proliant_raid(section: Mapping[str, HpProRaid]) -> DiscoveryResult:
    for raid in section:
        yield Service(item=raid)


def check_hp_proliant_raid(item: str, section: Mapping[str, HpProRaid]) -> CheckResult:
    if not (raid_stats := section.get(item)):
        return

    state, state_readable = _MAP_STATES.get(raid_stats.status, (State.UNKNOWN, "unknown"))
    yield Result(state=state, summary=f"Status: {state_readable}")
    yield Result(
        state=State.OK,
        summary=f"Logical volume size: {render.bytes(raid_stats.size_bytes)}",
    )

    # From CPQIDA-MIB:
    # This value is the percent complete of the rebuild.
    # This value is only valid if the Logical Drive Status is
    # rebuilding (7) or expanding (12).
    # If the value cannot be determined or a rebuild is not active,
    # the value is set to 4,294,967,295.
    if raid_stats.status not in {"7", "12"}:
        return

    if raid_stats.rebuild_percent == 4294967295:
        yield Result(state=State.OK, summary="Rebuild: undetermined")
        return

    yield Result(
        state=State.OK,
        summary=f"Rebuild: {render.percent(raid_stats.rebuild_percent)}",
    )


snmp_section_hp_proliant_raid = SimpleSNMPSection(
    name="hp_proliant_raid",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.3.2.3.1.1",
        oids=["2", "14", "4", "9", "12"],
    ),
    parse_function=parse_hp_proliant_raid,
)


check_plugin_hp_proliant_raid = CheckPlugin(
    name="hp_proliant_raid",
    service_name="Logical Device %s",
    discovery_function=discover_hp_proliant_raid,
    check_function=check_hp_proliant_raid,
)
