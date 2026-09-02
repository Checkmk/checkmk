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

# .1.3.6.1.4.1.10222.2.1.6.5.1.2.6.1 Fan 201 --> ICS-CHASSIS-MIB::icsChassisFanDescription.6.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.2.7.1 Fan 202 --> ICS-CHASSIS-MIB::icsChassisFanDescription.7.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.2.8.1 Fan 203 --> ICS-CHASSIS-MIB::icsChassisFanDescription.8.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.2.9.1 Fan 204 --> ICS-CHASSIS-MIB::icsChassisFanDescription.9.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.2.10.1 Fan 205 --> ICS-CHASSIS-MIB::icsChassisFanDescription.10.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.2.11.1 Fan 101 --> ICS-CHASSIS-MIB::icsChassisFanDescription.11.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.2.12.1 Fan 102 --> ICS-CHASSIS-MIB::icsChassisFanDescription.12.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.2.13.1 Fan 103 --> ICS-CHASSIS-MIB::icsChassisFanDescription.13.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.6.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.6.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.7.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.7.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.8.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.8.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.9.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.9.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.10.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.10.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.11.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.11.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.12.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.12.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.3.13.1 2 --> ICS-CHASSIS-MIB::icsChassisFanOperStatus.13.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.6.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.6.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.7.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.7.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.8.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.8.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.9.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.9.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.10.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.10.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.11.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.11.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.12.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.12.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.4.13.1 2 --> ICS-CHASSIS-MIB::icsChassisFanSpeed.13.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.6.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.6.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.7.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.7.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.8.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.8.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.9.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.9.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.10.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.10.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.11.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.11.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.12.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.12.1
# .1.3.6.1.4.1.10222.2.1.6.5.1.5.13.1 0 --> ICS-CHASSIS-MIB::icsChassisFanNonFatalErrors.13.1


def discover_intel_true_scale_fans(section: StringTable) -> DiscoveryResult:
    yield from (
        Service(item=fan_name.replace("Fan", "").strip())
        for fan_name, operstate, _speed_state in section
        if operstate != "4"
    )


def check_intel_true_scale_fans(item: str, section: StringTable) -> CheckResult:
    map_states = {
        "operational": {
            "1": (State.OK, "online"),
            "2": (State.OK, "operational"),
            "3": (State.CRIT, "failed"),
            "4": (State.WARN, "offline"),
        },
        "speed": {
            "1": (State.CRIT, "low"),
            "2": (State.OK, "normal"),
            "3": (State.CRIT, "high"),
            "4": (State.UNKNOWN, "unknown"),
        },
    }

    for fan_name, operstate, speedstate in section:
        if item == fan_name.replace("Fan", "").strip():
            for what, what_descr, what_mapping in [
                (operstate, "Operational", "operational"),
                (speedstate, "Speed", "speed"),
            ]:
                state, state_readable = map_states[what_mapping][what]
                yield Result(state=state, summary=f"{what_descr} status: {state_readable}")


def parse_intel_true_scale_fans(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_intel_true_scale_fans = SimpleSNMPSection(
    name="intel_true_scale_fans",
    detect=DETECT_INTEL_TRUE_SCALE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.10222.2.1.6.5.1",
        oids=["2", "3", "4"],
    ),
    parse_function=parse_intel_true_scale_fans,
)


check_plugin_intel_true_scale_fans = CheckPlugin(
    name="intel_true_scale_fans",
    service_name="Fan %s",
    discovery_function=discover_intel_true_scale_fans,
    check_function=check_intel_true_scale_fans,
)
