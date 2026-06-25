#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example for info:

# [['0'], ['1'], ['2'], ['3'], ['4'], ['5'], ['Critical'], ['Critical'],
# ['Warning'], ['Warning'], ['Warning'], ['Multiple fan failures'],
# ['Power Supply 1 AC Power Removed'], ['System Running Nonredundant Power'],
# ['Fan 7 Failure'], ['Fan 8 Failure']]

#   critical(0),
#   nonCritical(2),
#   systemLevel(4),
#   normal(255)


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def discover_ibm_rsa_health(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_ibm_rsa_health(section: StringTable) -> CheckResult:
    num_alerts = int((len(section) - 1) / 3)
    infotext = ""
    for i in range(num_alerts):
        state = section[num_alerts + 1 + i][0]
        text = section[num_alerts * 2 + 1 + i][0]
        if infotext != "":
            infotext += ", "
        infotext += f"{text}({state})"

    state = section[0][0]
    if state == "255":
        yield Result(state=State.OK, summary="no problem found")
        return
    if state in ["0", "2"]:
        yield Result(state=State.CRIT, summary=infotext)
        return
    if state == "4":
        yield Result(state=State.WARN, summary=infotext)
        return
    yield Result(state=State.UNKNOWN, summary=infotext)
    return


def parse_ibm_rsa_health(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ibm_rsa_health = SimpleSNMPSection(
    name="ibm_rsa_health",
    detect=contains(".1.3.6.1.2.1.1.1.0", "Remote Supervisor Adapter"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.1.2",
        oids=["7"],
    ),
    parse_function=parse_ibm_rsa_health,
)


check_plugin_ibm_rsa_health = CheckPlugin(
    name="ibm_rsa_health",
    service_name="System health",
    discovery_function=discover_ibm_rsa_health,
    check_function=check_ibm_rsa_health,
)
