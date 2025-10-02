#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.ups_modulys import DETECT_UPS_MODULYS


def inventory_ups_modulys_alarms(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_ups_modulys_alarms(section: StringTable) -> CheckResult:
    oiddef = {
        "1": Result(state=State.CRIT, summary="Disconnect"),
        "2": Result(state=State.CRIT, summary="Input power failure"),
        "3": Result(state=State.CRIT, summary="Low batteries"),
        "4": Result(state=State.WARN, summary="High load"),
        "5": Result(state=State.CRIT, summary="Severley high load"),
        "6": Result(state=State.CRIT, summary="On bypass"),
        "7": Result(state=State.CRIT, summary="General failure"),
        "8": Result(state=State.CRIT, summary="Battery ground fault"),
        "9": Result(state=State.OK, summary="UPS test in progress"),
        "10": Result(state=State.CRIT, summary="UPS test failure"),
        "11": Result(state=State.CRIT, summary="Fuse failure"),
        "12": Result(state=State.CRIT, summary="Output overload"),
        "13": Result(state=State.CRIT, summary="Output overcurrent"),
        "14": Result(state=State.CRIT, summary="Inverter abnormal"),
        "15": Result(state=State.CRIT, summary="Rectifier abnormal"),
        "16": Result(state=State.CRIT, summary="Reserve abnormal"),
        "17": Result(state=State.WARN, summary="On reserve"),
        "18": Result(state=State.CRIT, summary="Overheating"),
        "19": Result(state=State.CRIT, summary="Output abnormal"),
        "20": Result(state=State.CRIT, summary="Bypass bad"),
        "21": Result(state=State.OK, summary="In standby mode"),
        "22": Result(state=State.CRIT, summary="Charger failure"),
        "23": Result(state=State.CRIT, summary="Fan failure"),
        "24": Result(state=State.OK, summary="In economic mode"),
        "25": Result(state=State.WARN, summary="Output turned off"),
        "26": Result(state=State.WARN, summary="Smart shutdown in progress"),
        "27": Result(state=State.CRIT, summary="Emergency power off"),
        "28": Result(state=State.WARN, summary="Shutdown"),
        "29": Result(state=State.CRIT, summary="Output breaker open"),
    }

    result = False
    for oidend, flag in section:
        if flag and flag != "NULL" and int(flag):
            result = True
            yield oiddef[oidend]

    if not result:
        yield Result(state=State.OK, summary="No alarms")


def parse_ups_modulys_alarms(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ups_modulys_alarms = SimpleSNMPSection(
    name="ups_modulys_alarms",
    detect=DETECT_UPS_MODULYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2254.2.4",
        oids=[OIDEnd(), "9"],
    ),
    parse_function=parse_ups_modulys_alarms,
)


check_plugin_ups_modulys_alarms = CheckPlugin(
    name="ups_modulys_alarms",
    service_name="UPS Alarms",
    discovery_function=inventory_ups_modulys_alarms,
    check_function=check_ups_modulys_alarms,
)
