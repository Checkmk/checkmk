#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.intel.lib import DETECT_INTEL_TRUE_SCALE

# .1.3.6.1.4.1.10222.2.1.5.1.0 1 --> ICS-CHASSIS-MIB::icsChassisTemperatureStatus.0
# .1.3.6.1.4.1.10222.2.1.5.2.0 0 --> ICS-CHASSIS-MIB::icsChassisTemperatureWarning.0


def discover_intel_true_scale_chassis_temp(section: StringTable) -> DiscoveryResult:
    if section and section[0][0] != "6":
        yield Service()


def check_intel_true_scale_chassis_temp(section: StringTable) -> CheckResult:
    map_status = {
        "1": (State.OK, "normal"),
        "2": (State.WARN, "high"),
        "3": (State.CRIT, "excessively high"),
        "4": (State.WARN, "low"),
        "5": (State.CRIT, "excessively low"),
        "6": (State.UNKNOWN, "no sensor"),
        "7": (State.UNKNOWN, "unknown"),
    }
    map_warn_config = {
        "0": "unspecified",
        "1": "heed warning",
        "2": "ignore warning",
        "3": "no warning feature",
    }

    state, state_readable = map_status[section[0][0]]
    yield Result(
        state=state,
        summary=f"Status: {state_readable}, Warning configuration: {map_warn_config[section[0][1]]}",
    )


def parse_intel_true_scale_chassis_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_intel_true_scale_chassis_temp = SimpleSNMPSection(
    name="intel_true_scale_chassis_temp",
    detect=DETECT_INTEL_TRUE_SCALE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.10222.2.1.5",
        oids=["1", "2"],
    ),
    parse_function=parse_intel_true_scale_chassis_temp,
)


check_plugin_intel_true_scale_chassis_temp = CheckPlugin(
    name="intel_true_scale_chassis_temp",
    service_name="Temperature status chassis",
    discovery_function=discover_intel_true_scale_chassis_temp,
    check_function=check_intel_true_scale_chassis_temp,
)
