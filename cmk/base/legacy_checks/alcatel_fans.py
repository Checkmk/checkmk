#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.alcatel import DETECT_ALCATEL, DETECT_ALCATEL_AOS7


def parse_alcatel_fans(string_table: StringTable) -> StringTable:
    return string_table


def discover_alcatel_fans(info):
    for nr, _value in enumerate(info, 1):
        yield str(nr), None


def check_alcatel_fans(item, _no_params, info):
    fan_states = {
        0: "has no status",
        1: "not running",
        2: "running",
    }
    try:
        line = info[int(item) - 1]
        fan_state = int(line[0])
    except (ValueError, IndexError):
        return None

    state = 0 if fan_state == 2 else 2
    return state, "Fan " + fan_states.get(fan_state, "unknown (%s)" % fan_state)


check_info["alcatel_fans_aos7"] = LegacyCheckDefinition(
    parse_function=parse_alcatel_fans,
    detect=DETECT_ALCATEL_AOS7,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.1.1.3.1.1.11.1",
        oids=["2"],
    ),
    service_name="Fan %s",
    discovery_function=discover_alcatel_fans,
    check_function=check_alcatel_fans,
)


check_info["alcatel_fans"] = LegacyCheckDefinition(
    parse_function=parse_alcatel_fans,
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.1.1.3.1.1.11.1",
        oids=["2"],
    ),
    service_name="Fan %s",
    discovery_function=discover_alcatel_fans,
    check_function=check_alcatel_fans,
)
