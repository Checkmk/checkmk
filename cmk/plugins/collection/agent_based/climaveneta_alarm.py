#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

climaveneta_alarms = {
    # 20  : "Global (general)",
    21: "Maintenance Status",
    22: "Password",
    23: "High water 1erature",
    24: "High water 2erature",
    25: "Low room humidity",
    26: "High room humidity",
    27: "Low Roomerature",
    28: "High roomerature",
    29: "High air inleterature",
    30: "High air outleterature",
    31: "Room humid probe",
    32: "Room probe",
    33: "Inlet 1 probe",
    34: "Inlet 2 probe",
    35: "Inlet 3 probe",
    36: "Inlet 4 probe",
    37: "Outlet 1 probe",
    38: "Outlet 2 probe",
    39: "Outlet 3 probe",
    40: "Outlet 4 probe",
    41: "Water 1erature probe",
    42: "Water 2erature probe",
    43: "Door open",
    44: "EEPROM",
    45: "Fan 1 disconnected",
    46: "Fan 2 disconnected",
    47: "Fan 3 disconnected",
    48: "Fan 4 disconnected",
    49: "Dew point",
    50: "Flooding",
    51: "LAN",
    52: "Dirty filter",
    53: "Electronic thermostatic valve",
    54: "Low pressure",
    55: "High pressure",
    56: "Air flow",
    57: "Fire smoke",
    58: "I/O expansion",
    59: "Inverter",
    60: "Envelop",
    61: "Polygon inconsistent",
    62: "Delta pressure for inverter compressor",
    63: "Primary power supply",
    64: "Energy managment",
    65: "Low current humidif",
    66: "No water humidif",
    67: "High current humidif",
    68: "Humidifier Board Offline",
    69: "Life timer expired Reset/Clean cylinder",
    70: "Humidifier Drain",
    71: "Generic Humidifier",
    72: "Electric heater",
}


def inventory_climaveneta_alarm(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_climaveneta_alarm(section: StringTable) -> CheckResult:
    hit = False
    for oid_id, status in section:
        alarm_id = int(oid_id.split(".")[0])
        if alarm_id in climaveneta_alarms:
            if status != "0":
                hit = True
                yield Result(state=State.CRIT, summary="Alarm: %s" % climaveneta_alarms[alarm_id])
    if not hit:
        yield Result(state=State.OK, summary="No alarm state")


def parse_climaveneta_alarm(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_climaveneta_alarm = SimpleSNMPSection(
    name="climaveneta_alarm",
    detect=equals(".1.3.6.1.2.1.1.1.0", "pCO Gateway"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1",
        oids=[OIDEnd(), "1"],
    ),
    parse_function=parse_climaveneta_alarm,
)
check_plugin_climaveneta_alarm = CheckPlugin(
    name="climaveneta_alarm",
    service_name="Alarm Status",
    discovery_function=inventory_climaveneta_alarm,
    check_function=check_climaveneta_alarm,
)
