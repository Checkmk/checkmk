#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

_MODE_NAMES = {
    1: "TE",
    2: "NT",
}

_STATE_NAMES = {
    1: "Down",
    2: "UP",
}


def _saveint(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


@dataclass(frozen=True, kw_only=True)
class PriPort:
    state: int
    mode: int


Section = Mapping[str, PriPort]


def parse_innovaphone_priports_l2(string_table: StringTable) -> Section:
    return {
        item: PriPort(state=_saveint(state), mode=_saveint(mode))
        for item, state, mode in string_table
    }


def discover_innovaphone_priports_l2(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item, parameters={"mode": port.mode})
        for item, port in section.items()
        if port.state != 1
    )


def check_innovaphone_priports_l2(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (port := section.get(item)) is None:
        return

    yield Result(
        state=State.CRIT if port.state == 1 else State.OK,
        summary=f"State: {_STATE_NAMES[port.state]}",
    )
    yield Result(
        state=State.CRIT if port.mode != params["mode"] else State.OK,
        summary=f"Mode: {_MODE_NAMES[port.mode]}",
    )


snmp_section_innovaphone_priports_l2 = SimpleSNMPSection(
    name="innovaphone_priports_l2",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.6666"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6666.1.1.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_innovaphone_priports_l2,
)


check_plugin_innovaphone_priports_l2 = CheckPlugin(
    name="innovaphone_priports_l2",
    service_name="Port L2 %s",
    discovery_function=discover_innovaphone_priports_l2,
    check_function=check_innovaphone_priports_l2,
    check_default_parameters={},
)
