#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

check_info = {}

# Just an assumption, levels as in other fan checks


def discover_netextreme_fan(info):
    return [(line[0], {}) for line in info]


def check_netextreme_fan(item, params, info):
    map_fan_status = {
        "1": (0, "on"),
        "2": (0, "off"),
    }
    for fan_nr, fan_status, fan_speed_str in info:
        if fan_nr == item:
            state, state_readable = map_fan_status[fan_status]
            yield state, "Operational status: %s" % state_readable
            if fan_speed_str:
                yield check_fan(int(fan_speed_str), params)


def parse_netextreme_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["netextreme_fan"] = LegacyCheckDefinition(
    name="netextreme_fan",
    parse_function=parse_netextreme_fan,
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.9.1",
        oids=["1", "2", "4"],
    ),
    service_name="Fan %s",
    discovery_function=discover_netextreme_fan,
    check_function=check_netextreme_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
        "upper": (8000, 8400),
    },
)
