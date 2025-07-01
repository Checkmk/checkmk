#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping

from cmk.agent_based.v2 import (
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


@dataclasses.dataclass(frozen=True, kw_only=True)
class BDTMSTapeLibraryModule:
    module_status: str
    board_status: str
    power_supply_status: str


def parse_bdtms_tape_module(string_table: StringTable) -> dict[str, BDTMSTapeLibraryModule]:
    return {
        line[0]: BDTMSTapeLibraryModule(
            module_status=line[1].lower(),
            board_status=line[2].lower(),
            power_supply_status=line[3].lower(),
        )
        for line in string_table
    }


def discover_bdtms_tape_module(section: Mapping[str, BDTMSTapeLibraryModule]) -> DiscoveryResult:
    yield from (Service(item=device_id) for device_id in section)


def check_bdtms_tape_module(
    item: str,
    section: Mapping[str, BDTMSTapeLibraryModule],
) -> CheckResult:
    if not (module := section.get(item)):
        return

    def human_readable_state_to_monitoring_state(human_readable_state: str) -> State:
        return State.OK if human_readable_state == "ok" else State.CRIT

    yield Result(
        state=human_readable_state_to_monitoring_state(module.module_status),
        summary=f"Module: {module.module_status}",
    )
    yield Result(
        state=human_readable_state_to_monitoring_state(module.board_status),
        summary=f"Board: {module.board_status}",
    )
    yield Result(
        state=human_readable_state_to_monitoring_state(module.power_supply_status),
        summary=f"Power supply: {module.power_supply_status}",
    )


snmp_section_bdtms_tape_module = SimpleSNMPSection(
    name="bdtms_tape_module",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.77.83.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.2.4.1",
        oids=[OIDEnd(), "4", "5", "6"],
    ),
    parse_function=parse_bdtms_tape_module,
)

check_plugin_bdtms_tape_module = CheckPlugin(
    name="bdtms_tape_module",
    service_name="Tape Library Module %s",
    discovery_function=discover_bdtms_tape_module,
    check_function=check_bdtms_tape_module,
)
