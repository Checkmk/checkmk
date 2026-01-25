#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.meinberg.liblantime import DETECT_MBG_LANTIME_NG

check_info = {}

type Section = StringTable


def discover_mbg_lantime_ng_power(info: Section) -> LegacyDiscoveryResult:
    for line in info:
        yield line[0], {}


def check_mbg_lantime_ng_power(item: str, _no_params: object, info: Section) -> LegacyCheckResult:
    power_states = {
        "0": (2, "not available"),
        "1": (2, "down"),
        "2": (0, "up"),
    }
    for index, power_status in info:
        if item == index:
            power_state, power_state_name = power_states[power_status]
            infotext = "Status: %s" % power_state_name
            yield power_state, infotext
            return


def parse_mbg_lantime_ng_power(string_table: StringTable) -> StringTable:
    return string_table


check_info["mbg_lantime_ng_power"] = LegacyCheckDefinition(
    name="mbg_lantime_ng_power",
    parse_function=parse_mbg_lantime_ng_power,
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.5.0.2.1",
        oids=["1", "2"],
    ),
    service_name="Power Supply %s",
    discovery_function=discover_mbg_lantime_ng_power,
    check_function=check_mbg_lantime_ng_power,
)
