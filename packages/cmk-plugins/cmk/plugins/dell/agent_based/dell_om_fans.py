#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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
    State,
    StringTable,
)
from cmk.plugins.dell.lib import DETECT_OPENMANAGE
from cmk.plugins.lib.fan import check_fan

_TRANSLATE_STATUS: Mapping[str, tuple[State, str]] = {
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


def _construct_levels(
    warn_upper: str, crit_upper: str, warn_lower: str, crit_lower: str
) -> Mapping[str, Any]:
    # We've seen several possibilities:
    # - 1, 2, 3, 4
    # - "", "", 3, 4
    # - "", "", "", 4
    params: dict[str, tuple[int, int]] = {}

    if warn_lower not in ["", None] and crit_lower not in ["", None]:
        params["lower"] = (int(warn_lower), int(crit_lower))
    elif crit_lower not in ["", None]:
        params["lower"] = (int(crit_lower), int(crit_lower))

    if warn_upper not in ["", None] and crit_upper not in ["", None]:
        params["upper"] = (int(warn_upper), int(crit_upper))
    elif crit_upper not in ["", None]:
        params["upper"] = (int(crit_upper), int(crit_upper))

    return params


def discover_dell_om_fans(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_dell_om_fans(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for index, status, value, name, warn_upper, crit_upper, warn_lower, crit_lower in section:
        if index == item:
            state, state_readable = _TRANSLATE_STATUS[status]
            yield Result(state=state, summary=f"Status: {state_readable}, Name: {name}")
            fan_params = (
                params
                if params
                else _construct_levels(warn_upper, crit_upper, warn_lower, crit_lower)
            )
            yield from check_fan(int(value), fan_params)


def parse_dell_om_fans(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_om_fans = SimpleSNMPSection(
    name="dell_om_fans",
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.700.12.1",
        oids=["2", "5", "6", "8", "10", "11", "12", "13"],
    ),
    parse_function=parse_dell_om_fans,
)

check_plugin_dell_om_fans = CheckPlugin(
    name="dell_om_fans",
    service_name="Fan %s",
    discovery_function=discover_dell_om_fans,
    check_function=check_dell_om_fans,
    check_default_parameters={},
    check_ruleset_name="hw_fans",
)
