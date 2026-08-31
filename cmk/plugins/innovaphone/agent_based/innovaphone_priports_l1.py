#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_rate,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

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
    sigloss: int
    slip: int


Section = Mapping[str, PriPort]


def parse_innovaphone_priports_l1(string_table: StringTable) -> Section:
    return {
        item: PriPort(
            state=_saveint(state),
            sigloss=_saveint(sigloss),
            slip=_saveint(slip),
        )
        for item, state, sigloss, slip in string_table
    }


def discover_innovaphone_priports_l1(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item, parameters={"err_slip_count": port.slip})
        for item, port in section.items()
        if port.state != 1
    )


def check_innovaphone_priports_l1(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (port := section.get(item)) is None:
        return

    yield Result(
        state=State.OK if port.state == 2 else State.CRIT,
        summary=f"Current state is {_STATE_NAMES[port.state]}",
    )

    sigloss_per_sec = get_rate(
        get_value_store(),
        f"innovaphone_priports_l1.{item}",
        time.time(),
        port.sigloss,
        raise_overflow=True,
    )
    if sigloss_per_sec > 0:
        yield Result(state=State.CRIT, summary=f"Signal loss is {sigloss_per_sec:.2f}/sec")

    if port.slip > params.get("err_slip_count", 0):
        yield Result(state=State.CRIT, summary=f"Slip error count at {port.slip}")


snmp_section_innovaphone_priports_l1 = SimpleSNMPSection(
    name="innovaphone_priports_l1",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.6666"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6666.1.2.1",
        oids=["1", "2", "5", "9"],
    ),
    parse_function=parse_innovaphone_priports_l1,
)


check_plugin_innovaphone_priports_l1 = CheckPlugin(
    name="innovaphone_priports_l1",
    service_name="Port L1 %s",
    discovery_function=discover_innovaphone_priports_l1,
    check_function=check_innovaphone_priports_l1,
    check_default_parameters={},
)
