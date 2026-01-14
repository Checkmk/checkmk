#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Iterable, Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.plugins.genua.lib import DETECT_GENUA

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_genua_fan(string_table: list[StringTable]) -> Iterable[tuple[str, dict[str, object]]]:
    for tree in string_table:
        if not tree:
            continue
        for name, _reading, _state in tree:
            yield name, {}
        return


def check_genua_fan(item, params, info):
    # remove empty elements due to alternative enterprise id in snmp_info
    info = [_f for _f in info if _f]

    map_states = {
        "1": (0, "OK"),
        "2": (1, "warning"),
        "3": (2, "critical"),
        "4": (2, "unknown"),
        "5": (2, "unknown"),
        "6": (2, "unknown"),
    }

    for line in info[0]:
        fanName, fanRPM, fanState = line
        if fanName != item:
            continue

        rpm = saveint(fanRPM)
        state, state_readable = map_states[fanState]
        yield state, "Status: %s" % state_readable
        yield check_fan(rpm, params)


def parse_genua_fan(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["genua_fan"] = LegacyCheckDefinition(
    name="genua_fan",
    parse_function=parse_genua_fan,
    detect=DETECT_GENUA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3717.2.1.1.1.1",
            oids=["2", "3", "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3137.2.1.1.1.1",
            oids=["2", "3", "4"],
        ),
    ],
    service_name="FAN %s",
    discovery_function=discover_genua_fan,
    check_function=check_genua_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
        "upper": (8000, 8400),
    },
)
