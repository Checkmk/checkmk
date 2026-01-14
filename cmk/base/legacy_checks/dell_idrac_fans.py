#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.fan import check_fan

check_info = {}

DELL_IDRAC_FANS_STATE_MAP = {
    "1": (3, "OTHER"),
    "2": (3, "UNKNOWN"),
    "3": (0, "OK"),
    "4": (1, "NON CRITICAL UPPER"),
    "5": (2, "CRITICAL UPPER"),
    "6": (2, "NON RECOVERABLE UPPER"),
    "7": (1, "NON CRITICAL LOWER"),
    "8": (2, "CRITICAL LOWER"),
    "9": (2, "NON RECOVERABLE LOWER"),
    "10": (2, "FAILED"),
}


def discover_dell_idrac_fans(info):
    for index, state, _value, _name, _warn_upper, _crit_upper, _warn_lower, _crit_lower in info:
        # don't discover fans with a state of other or unknown
        if DELL_IDRAC_FANS_STATE_MAP[state][1] not in ("OTHER", "UNKNOWN"):
            yield index, {}


def check_dell_idrac_fans(item, params, info):
    for index, status, value, name, warn_upper, crit_upper, warn_lower, crit_lower in info:
        if index == item:
            state, state_readable = DELL_IDRAC_FANS_STATE_MAP[status]
            yield state, f"Status: {state_readable}, Name: {name}"
            if state_readable in ("OTHER", "UNKNOWN", "FAILED"):
                return

            value = int(value)
            if not params:
                params = {"lower": (int(warn_lower), int(crit_lower))}
                if not warn_upper == "" and crit_upper == "":
                    params["upper"] = (int(warn_upper), int(crit_upper))

            yield check_fan(value, params)


def parse_dell_idrac_fans(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_idrac_fans"] = LegacyCheckDefinition(
    name="dell_idrac_fans",
    parse_function=parse_dell_idrac_fans,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.5"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.4.700.12.1",
        oids=["2", "5", "6", "8", "10", "11", "12", "13"],
    ),
    service_name="Fan %s",
    discovery_function=discover_dell_idrac_fans,
    check_function=check_dell_idrac_fans,
    check_ruleset_name="hw_fans",
)
