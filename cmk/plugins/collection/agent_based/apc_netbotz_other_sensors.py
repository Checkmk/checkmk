#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Max. eigth sensors
# .1.3.6.1.4.1.5528.100.4.2.10.1.4.399845582 Wasserstand_FG1
# .1.3.6.1.4.1.5528.100.4.2.10.1.4.3502248167 Ethernet Link Status
# .1.3.6.1.4.1.5528.100.4.2.10.1.4.3823829717 A-Link Bus Power
# .1.3.6.1.4.1.5528.100.4.2.10.1.3.399845582 0
# .1.3.6.1.4.1.5528.100.4.2.10.1.3.3502248167 0
# .1.3.6.1.4.1.5528.100.4.2.10.1.3.3823829717 0
# .1.3.6.1.4.1.5528.100.4.2.10.1.7.399845582 No Leak
# .1.3.6.1.4.1.5528.100.4.2.10.1.7.3502248167 Up
# .1.3.6.1.4.1.5528.100.4.2.10.1.7.3823829717 OK

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


@dataclass(frozen=True)
class Sensor:
    label: str
    error_state: str
    state_readable: str


def parse_apc_netbotz_other_sensors(string_table: StringTable) -> Sequence[Sensor]:
    return [
        Sensor(label=label, error_state=error_state, state_readable=state_readable)
        for label, error_state, state_readable in string_table
    ]


snmp_section_apc_netbotz_v2_other_sensors = SimpleSNMPSection(
    name="apc_netbotz_v2_other_sensors",
    parse_function=parse_apc_netbotz_other_sensors,
    parsed_section_name="apc_netbotz_other_sensors",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5528.100.4.2.10.1",
        oids=[
            "4",  # NETBOTZV2-MIB::otherNumericSensorLabel
            "3",  # NETBOTZV2-MIB::otherNumericSensorErrorStatus
            "7",  # NETBOTZV2-MIB::otherNumericSensorValueStr
        ],
    ),
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5528.100.20.10"),
)

snmp_section_apc_netbotz_50_other_sensors = SimpleSNMPSection(
    name="apc_netbotz_50_other_sensors",
    parse_function=parse_apc_netbotz_other_sensors,
    parsed_section_name="apc_netbotz_other_sensors",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52674.500.4.2.10.1",
        oids=[
            "4",  # NETBOTZ50-MIB::otherNumericSensorLabel
            "3",  # NETBOTZ50-MIB::otherNumericSensorErrorStatus
            "7",  # NETBOTZ50-MIB::otherNumericSensorValueStr
        ],
    ),
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.52674.500"),
)


# MIB: The sensor reading shown as a string (or empty string
# if it is not plugged into a port).
def discover_apc_netbotz_other_sensors(section: Sequence[Sensor]) -> DiscoveryResult:
    for sensor in section:
        if sensor.state_readable != "":
            yield Service()
            return


def check_apc_netbotz_other_sensors(section: Sequence[Sensor]) -> CheckResult:
    count_ok_sensors = 0
    for sensor in section:
        if sensor.state_readable != "":
            if sensor.state_readable != "OK":
                state_readable = sensor.state_readable.lower()

            if sensor.error_state == "0":
                count_ok_sensors += 1
            else:
                yield Result(state=State.CRIT, summary=f"{sensor.label}: {state_readable}")

    if count_ok_sensors > 0:
        yield Result(state=State.OK, summary=f"{count_ok_sensors} sensors are OK")


check_plugin_apc_netbotz_other_sensors = CheckPlugin(
    name="apc_netbotz_other_sensors",
    service_name="Numeric sensors summary",
    discovery_function=discover_apc_netbotz_other_sensors,
    check_function=check_apc_netbotz_other_sensors,
)
