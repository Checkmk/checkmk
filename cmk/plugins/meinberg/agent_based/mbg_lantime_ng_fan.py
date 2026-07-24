#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
from cmk.plugins.meinberg.liblantime import DETECT_MBG_LANTIME_NG


def parse_mbg_lantime_ng_fan(string_table: StringTable) -> dict[str, dict[str, tuple[State, str]]]:
    parsed: dict[str, dict[str, tuple[State, str]]] = {}
    fan_states: dict[str, tuple[State, str]] = {
        "0": (State.UNKNOWN, "not available"),
        "1": (State.CRIT, "off"),
        "2": (State.OK, "on"),
    }
    fan_errors: dict[str, tuple[State, str]] = {
        "0": (State.OK, "not available"),
        "1": (State.OK, "no"),
        "2": (State.CRIT, "yes"),
    }

    for index, fan_status, fan_error in string_table:
        if not index:
            continue

        parsed.setdefault(
            index,
            {
                "status": fan_states.get(fan_status, (State.UNKNOWN, "not available")),
                "error": fan_errors.get(fan_error, (State.UNKNOWN, "not available")),
            },
        )

    return parsed


def discover_mbg_lantime_ng_fan(
    section: dict[str, dict[str, tuple[State, str]]],
) -> DiscoveryResult:
    yield from (
        Service(item=item) for item, data in section.items() if data["status"][1] != "not available"
    )


def check_mbg_lantime_ng_fan(
    item: str, section: dict[str, dict[str, tuple[State, str]]]
) -> CheckResult:
    if not (data := section.get(item)):
        return

    status_state, status_name = data["status"]
    yield Result(state=status_state, summary=f"Status: {status_name}")

    error_state, error_name = data["error"]
    yield Result(state=error_state, summary=f"Errors: {error_name}")


snmp_section_mbg_lantime_ng_fan = SimpleSNMPSection(
    name="mbg_lantime_ng_fan",
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.5.1.2.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_mbg_lantime_ng_fan,
)


check_plugin_mbg_lantime_ng_fan = CheckPlugin(
    name="mbg_lantime_ng_fan",
    service_name="Fan %s",
    discovery_function=discover_mbg_lantime_ng_fan,
    check_function=check_mbg_lantime_ng_fan,
)
