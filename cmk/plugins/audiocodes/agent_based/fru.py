#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .lib import DETECT_AUDIOCODES

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


def parse_audiocodes_fru(string_table: Sequence[StringTable]) -> Mapping[str, FRUModule] | None:
    if not all(string_table):
        return None

    name_by_module_index = {module[0]: f"{module[1]} {module[0]}" for module in string_table[0]}
    modules_by_index = {
        module[0]: FRUModule(
            action=Action(*ACTION_MAPPING[module[1]]),
            status=Status(*STATUS_MAPPING[module[2]]),
        )
        for module in string_table[1]
    }

    return {
        name: module
        for module_idx, module in modules_by_index.items()
        if (name := name_by_module_index.get(module_idx))
    }


snmp_section_audiocodes_fru = SNMPSection(
    name="audiocodes_fru",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[
                OIDEnd(),
                "2",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
            oids=[
                OIDEnd(),
                "13",  # acSysModuleFRUaction
                "14",  # acSysModuleFRUstatus
            ],
        ),
    ],
    parse_function=parse_audiocodes_fru,
)


def discover_audiocodes_fru(section: Mapping[str, FRUModule]) -> DiscoveryResult:
    yield from (Service(item=module_name) for module_name in section)


def check_audiocodes_fru(item: str, section: Mapping[str, FRUModule]) -> CheckResult:
    if (module := section.get(item)) is None:
        return

    yield Result(
        state=module.action.state,
        summary=f"Action: {module.action.name}",
    )
    yield Result(
        state=module.status.state,
        summary=f"Status: {module.status.name}",
    )


check_plugin_audiocodes_fru = CheckPlugin(
    name="audiocodes_fru",
    service_name="AudioCodes FRU %s",
    discovery_function=discover_audiocodes_fru,
    check_function=check_audiocodes_fru,
)
