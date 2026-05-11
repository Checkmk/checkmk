#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

hp_sts_drvbox_type_map = {
    "1": "other",
    "2": "ProLiant Storage System",
    "3": "ProLiant-2 Storage System",
    "4": "internal ProLiant-2 Storage System",
    "5": "proLiant2DuplexTop",
    "6": "proLiant2DuplexBottom",
    "7": "proLiant2InternalDuplexTop",
    "8": "proLiant2InternalDuplexBottom",
}

hp_sts_drvbox_cond_map: Mapping[str, tuple[State | None, str]] = {
    "1": (State.UNKNOWN, "other"),
    "2": (State.OK, "ok"),
    "3": (State.WARN, "degraded"),
    "4": (State.CRIT, "failed"),
}

hp_sts_drvbox_fan_map: Mapping[str, tuple[State | None, str]] = {
    "1": (State.UNKNOWN, "other"),
    "2": (State.OK, "ok"),
    "3": (State.CRIT, "failed"),
    "4": (None, "noFan"),
    "5": (State.WARN, "degraded"),
}

hp_sts_drvbox_temp_map: Mapping[str, tuple[State | None, str]] = {
    "1": (State.UNKNOWN, "other"),
    "2": (State.OK, "ok"),
    "3": (State.WARN, "degraded"),
    "4": (State.CRIT, "failed"),
    "5": (None, "noTemp"),
}

hp_sts_drvbox_sp_map: Mapping[str, tuple[State | None, str]] = {
    "1": (State.UNKNOWN, "other"),
    "2": (State.OK, "sidePanelInPlace"),
    "3": (State.CRIT, "sidePanelRemoved"),
    "4": (None, "noSidePanelStatus"),
}

hp_sts_drvbox_power_map: Mapping[str, tuple[State | None, str]] = {
    "1": (State.UNKNOWN, "other"),
    "2": (State.OK, "ok"),
    "3": (State.WARN, "degraded"),
    "4": (State.CRIT, "failed"),
    "5": (None, "noFltTolPower"),
}


Section = Sequence[Sequence[str]]


def parse_hp_sts_drvbox(string_table: StringTable) -> Section:
    return string_table


def discover_hp_sts_drvbox(section: Section) -> DiscoveryResult:
    # only inventorize rows with "model" set
    yield from (Service(item=f"{line[0]}/{line[1]}") for line in section if line[3] != "")


def check_hp_sts_drvbox(item: str, section: Section) -> CheckResult:
    for line in section:
        if f"{line[0]}/{line[1]}" != item:
            continue
        (
            _c_index,
            _b_index,
            ty,
            model,
            fan_status,
            cond,
            temp_status,
            sp_status,
            pwr_status,
            serial,
            loc,
        ) = line

        for val, label, map_ in [
            (fan_status, "Fan-Status", hp_sts_drvbox_fan_map),
            (cond, "Condition", hp_sts_drvbox_cond_map),
            (temp_status, "Temp-Status", hp_sts_drvbox_temp_map),
            (sp_status, "Sidepanel-Status", hp_sts_drvbox_sp_map),
            (pwr_status, "Power-Status", hp_sts_drvbox_power_map),
        ]:
            state, name = map_[val]
            if state is None:
                continue  # skip unsupported checks
            yield Result(state=state, summary=f"{label}: {name}")

        yield Result(
            state=State.OK,
            summary=(
                f"Type: {hp_sts_drvbox_type_map.get(ty, 'unknown')}, "
                f"Model: {model}, Serial: {serial}, Location: {loc}"
            ),
        )
        return
    yield Result(state=State.UNKNOWN, summary="Controller not found in snmp data")


snmp_section_hp_sts_drvbox = SimpleSNMPSection(
    name="hp_sts_drvbox",
    parse_function=parse_hp_sts_drvbox,
    detect=contains(".1.3.6.1.4.1.232.2.2.4.2.0", "proliant"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.8.2.1.1",
        oids=["1", "2", "3", "4", "7", "8", "9", "10", "11", "17", "23"],
    ),
)


check_plugin_hp_sts_drvbox = CheckPlugin(
    name="hp_sts_drvbox",
    service_name="Drive Box %s",
    discovery_function=discover_hp_sts_drvbox,
    check_function=check_hp_sts_drvbox,
)
