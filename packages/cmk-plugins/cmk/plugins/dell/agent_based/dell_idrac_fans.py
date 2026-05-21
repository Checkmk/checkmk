#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan

MaybeInt = int | None


DELL_IDRAC_FANS_STATE_MAP = {
    "1": (State.UNKNOWN, "OTHER"),
    "2": (State.UNKNOWN, "UNKNOWN"),
    "3": (State.OK, "OK"),
    "4": (State.WARN, "NON CRITICAL UPPER"),
    "5": (State.CRIT, "CRITICAL UPPER"),
    "6": (State.CRIT, "NON RECOVERABLE UPPER"),
    "7": (State.WARN, "NON CRITICAL LOWER"),
    "8": (State.CRIT, "CRITICAL LOWER"),
    "9": (State.CRIT, "NON RECOVERABLE LOWER"),
    "10": (State.CRIT, "FAILED"),
}


def discover_dell_idrac_fans(section: StringTable) -> DiscoveryResult:
    for index, state, _value, _name, _warn_upper, _crit_upper, _warn_lower, _crit_lower in section:
        # don't discover fans with a state of other or unknown
        if DELL_IDRAC_FANS_STATE_MAP[state][1] not in ("OTHER", "UNKNOWN"):
            yield Service(item=index)


def _to_int_or_none(value: str) -> MaybeInt:
    try:
        return int(value)
    except ValueError:
        return None


def check_dell_idrac_fans(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for index, status, value, name, warn_upper, crit_upper, warn_lower, crit_lower in section:
        if index == item:
            state, state_readable = DELL_IDRAC_FANS_STATE_MAP[status]
            yield Result(state=state, summary=f"Status: {state_readable}, Name: {name}")
            if state_readable in ("OTHER", "UNKNOWN", "FAILED"):
                return

            rpm = int(value)
            if params:
                yield from check_fan(rpm, params)
                return

            fan_params: dict[str, tuple[MaybeInt, MaybeInt] | None] = {}
            levels_lower = (_to_int_or_none(warn_lower), _to_int_or_none(crit_lower))
            levels_upper = (_to_int_or_none(warn_upper), _to_int_or_none(crit_upper))
            if levels_lower != (None, None):
                fan_params["lower"] = levels_lower
            if levels_upper != (None, None):
                fan_params["upper"] = levels_upper

            yield from check_fan(rpm, fan_params)


def parse_dell_idrac_fans(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_idrac_fans = SimpleSNMPSection(
    name="dell_idrac_fans",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.5"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.4.700.12.1",
        oids=["2", "5", "6", "8", "10", "11", "12", "13"],
    ),
    parse_function=parse_dell_idrac_fans,
)


check_plugin_dell_idrac_fans = CheckPlugin(
    name="dell_idrac_fans",
    service_name="Fan %s",
    discovery_function=discover_dell_idrac_fans,
    check_function=check_dell_idrac_fans,
    check_default_parameters={},
    check_ruleset_name="hw_fans",
)
