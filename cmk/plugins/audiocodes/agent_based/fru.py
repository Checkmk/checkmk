#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .lib import data_by_item, DETECT_AUDIOCODES

ACTION_MAPPING = {
    "0": ("Invalid action", State.UNKNOWN),
    "1": ("Action done", State.OK),
    "2": ("Out of service", State.WARN),
    "3": ("Back to service", State.OK),
    "4": ("Not applicable", State.UNKNOWN),
}

STATUS_MAPPING = {
    "0": ("Invalid status", State.UNKNOWN),
    "1": ("Module doesn't exist", State.OK),
    "2": ("Module exists and ok", State.OK),
    "3": ("Module Ouf of service", State.CRIT),
    "4": ("Module Back to service start", State.OK),
    "5": ("Module mismatch", State.CRIT),
    "6": ("Module faulty", State.CRIT),
    "7": ("Not applicable", State.UNKNOWN),
}


@dataclass(frozen=True)
class Action:
    name: str
    state: State


@dataclass(frozen=True)
class Status:
    name: str
    state: State


@dataclass(frozen=True, kw_only=True)
class FRUModule:
    action: Action
    status: Status


def parse_audiocodes_fru(string_table: StringTable) -> Mapping[str, FRUModule] | None:
    if not string_table:
        return None

    return {
        module[0]: FRUModule(
            action=Action(*ACTION_MAPPING[module[1]]),
            status=Status(*STATUS_MAPPING[module[2]]),
        )
        for module in string_table
    }


snmp_section_audiocodes_fru = SimpleSNMPSection(
    name="audiocodes_fru",
    detect=DETECT_AUDIOCODES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
        oids=[
            OIDEnd(),
            "13",  # acSysModuleFRUaction
            "14",  # acSysModuleFRUstatus
        ],
    ),
    parse_function=parse_audiocodes_fru,
)


def discover_audiocodes_fru(
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_fru: Mapping[str, FRUModule] | None,
) -> DiscoveryResult:
    if not section_audiocodes_module_names or not section_audiocodes_fru:
        return

    yield from (
        Service(item=item)
        for item in data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_fru,
        )
    )


def check_audiocodes_fru(
    item: str,
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_fru: Mapping[str, FRUModule] | None,
) -> CheckResult:
    if not section_audiocodes_fru or not section_audiocodes_module_names:
        return

    if (
        module_fru := data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_fru,
        ).get(item)
    ) is None:
        return

    yield Result(
        state=module_fru.action.state,
        summary=f"Action: {module_fru.action.name}",
    )
    yield Result(
        state=module_fru.status.state,
        summary=f"Status: {module_fru.status.name}",
    )


check_plugin_audiocodes_fru = CheckPlugin(
    name="audiocodes_fru",
    service_name="AudioCodes FRU %s",
    sections=["audiocodes_module_names", "audiocodes_fru"],
    discovery_function=discover_audiocodes_fru,
    check_function=check_audiocodes_fru,
)
