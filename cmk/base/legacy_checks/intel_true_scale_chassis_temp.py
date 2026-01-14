#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.intel.lib import DETECT_INTEL_TRUE_SCALE

check_info = {}

# .1.3.6.1.4.1.10222.2.1.5.1.0 1 --> ICS-CHASSIS-MIB::icsChassisTemperatureStatus.0
# .1.3.6.1.4.1.10222.2.1.5.2.0 0 --> ICS-CHASSIS-MIB::icsChassisTemperatureWarning.0


def discover_intel_true_scale_chassis_temp(info):
    if info and info[0][0] != "6":
        return [(None, None)]
    return []


def check_intel_true_scale_chassis_temp(_no_item, _no_params, info):
    map_status = {
        "1": (0, "normal"),
        "2": (1, "high"),
        "3": (2, "excessively high"),
        "4": (1, "low"),
        "5": (2, "excessively low"),
        "6": (3, "no sensor"),
        "7": (3, "unknown"),
    }
    map_warn_config = {
        "0": "unspecified",
        "1": "heed warning",
        "2": "ignore warning",
        "3": "no warning feature",
    }

    state, state_readable = map_status[info[0][0]]
    return state, f"Status: {state_readable}, Warning configuration: {map_warn_config[info[0][1]]}"


def parse_intel_true_scale_chassis_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["intel_true_scale_chassis_temp"] = LegacyCheckDefinition(
    name="intel_true_scale_chassis_temp",
    parse_function=parse_intel_true_scale_chassis_temp,
    detect=DETECT_INTEL_TRUE_SCALE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.10222.2.1.5",
        oids=["1", "2"],
    ),
    service_name="Temperature status chassis",
    discovery_function=discover_intel_true_scale_chassis_temp,
    check_function=check_intel_true_scale_chassis_temp,
)
