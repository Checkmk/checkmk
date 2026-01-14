#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN

check_info = {}


def discover_huawei_osn_fan(info):
    for line in info:
        yield (line[0], None)


def check_huawei_osn_fan(item, params, info):
    translate_speed = {
        "0": (1, "stop"),
        "1": (0, "low"),
        "2": (0, "mid-low"),
        "3": (0, "mid"),
        "4": (0, "mid-high"),
        "5": (1, "high"),
    }
    for line in info:
        if item == line[0]:
            state, state_readable = translate_speed[line[1]]
            return state, "Speed: %s" % state_readable
    return None


def parse_huawei_osn_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["huawei_osn_fan"] = LegacyCheckDefinition(
    name="huawei_osn_fan",
    parse_function=parse_huawei_osn_fan,
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.4.70.20.10.10.1",
        oids=["1", "2"],
    ),
    service_name="Unit %s (Fan)",
    discovery_function=discover_huawei_osn_fan,
    check_function=check_huawei_osn_fan,
)
