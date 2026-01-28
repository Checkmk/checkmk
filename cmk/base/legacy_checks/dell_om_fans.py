#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"


from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.plugins.dell.lib import DETECT_OPENMANAGE

check_info = {}


def discover_dell_om_fans(info: StringTable) -> LegacyDiscoveryResult:
    for line in info:
        yield (line[0], {})


def _construct_levels(
    warn_upper: str, crit_upper: str, warn_lower: str, crit_lower: str
) -> tuple[tuple[int, int] | tuple[None, None], tuple[int, int] | tuple[None, None]]:
    # We've seen several possibilities:
    # - 1, 2, 3, 4
    # - "", "", 3, 4
    # - "", "", "", 4
    if warn_lower not in ["", None] and crit_lower not in ["", None]:
        lower: tuple[int, int] | tuple[None, None] = (int(warn_lower), int(crit_lower))
    elif crit_lower not in ["", None]:
        lower = (int(crit_lower), int(crit_lower))
    else:
        lower = (None, None)

    if warn_upper not in ["", None] and crit_upper not in ["", None]:
        upper: tuple[int, int] | tuple[None, None] = (int(warn_upper), int(crit_upper))
    elif crit_upper not in ["", None]:
        upper = (int(crit_upper), int(crit_upper))
    else:
        upper = (None, None)

    return lower, upper


def check_dell_om_fans(
    item: str, params: Mapping[str, object], info: StringTable
) -> LegacyCheckResult:
    translate_status = {
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

    for index, status, value, name, warn_upper, crit_upper, warn_lower, crit_lower in info:
        if index == item:
            state, state_readable = translate_status[status]
            yield state, f"Status: {state_readable}, Name: {name}"
            if params:
                constructed_params = params
            else:
                lower, upper = _construct_levels(warn_upper, crit_upper, warn_lower, crit_lower)
                constructed_params = {
                    "lower": lower,
                    "upper": upper,
                }
            yield check_fan(int(value), constructed_params)


def parse_dell_om_fans(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_om_fans"] = LegacyCheckDefinition(
    name="dell_om_fans",
    parse_function=parse_dell_om_fans,
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.700.12.1",
        oids=["2", "5", "6", "8", "10", "11", "12", "13"],
    ),
    service_name="Fan %s",
    discovery_function=discover_dell_om_fans,
    check_function=check_dell_om_fans,
    check_ruleset_name="hw_fans",
)
