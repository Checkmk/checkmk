#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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

_STATUS_MAP: dict[str, tuple[State, str]] = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.OK, "unused"),
    "3": (State.OK, "ok"),
    "4": (State.WARN, "warning"),
    "5": (State.CRIT, "critical"),
    "6": (State.CRIT, "nonrecoverable"),
}


def parse_hp_eml_sum(string_table: StringTable) -> StringTable:
    return string_table


def discover_hp_eml_sum(section: StringTable) -> DiscoveryResult:
    if section and section[0]:
        yield Service()


def check_hp_eml_sum(section: StringTable) -> CheckResult:
    if not section or not section[0]:
        yield Result(state=State.UNKNOWN, summary="Summary status information missing")
        return

    op_status, manufacturer, model, serial, version = section[0]
    state, status_txt = _STATUS_MAP.get(
        op_status, (State.UNKNOWN, f"unhandled op_status ({op_status})")
    )

    yield Result(
        state=state,
        summary=(
            f'Summary State is "{status_txt}", Manufacturer: {manufacturer}, '
            f"Model: {model}, Serial: {serial}, Version: {version}"
        ),
    )


snmp_section_hp_eml_sum = SimpleSNMPSection(
    name="hp_eml_sum",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11.10.2.1.3.20"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1",
        oids=["3", "7", "9", "10", "11"],
    ),
    parse_function=parse_hp_eml_sum,
)


check_plugin_hp_eml_sum = CheckPlugin(
    name="hp_eml_sum",
    service_name="Summary Status",
    discovery_function=discover_hp_eml_sum,
    check_function=check_hp_eml_sum,
)
