#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.detection import DETECT_NEVER

# snmp_scan_function
# .1.3.6.1.2.1.1.4.0 = STRING: x.name@green-cooling.de < green-cooling match
# .1.3.6.1.2.1.1.5.0 = STRING: pCOWeb                    < pcoweb match
# .1.3.6.1.4.1.9839.1                                    < exists

# snmp_info
# .1.3.6.1.4.1.9839.2.1.1.31.0 = INTEGER: 0   < Waterloss
# .1.3.6.1.4.1.9839.2.1.1.51.0 = INTEGER: 1   < Global
# .1.3.6.1.4.1.9839.2.1.1.67.0 = INTEGER: 0   < Unit in Emergeny operation
# .1.3.6.1.4.1.9839.2.1.2.6.0 = INTEGER:  246 < Humidifier: Relative Humidity


def inventory_carel_uniflair_cooling(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_carel_uniflair_cooling(section: StringTable) -> CheckResult:
    waterloss, global_status, ermergency_op, r_humidity = section[0]

    err_waterloss = waterloss != "0"
    err_global_status = global_status != "1"
    err_emergency_op = ermergency_op != "0"
    humidity = float(r_humidity) / 10

    output = ""
    output = output + ("Global Status: %s" % (err_global_status and "Error(!!), " or "OK, "))
    output = output + (
        "Emergency Operation: %s" % (err_emergency_op and "Active(!!), " or "Inactive, ")
    )
    output = output + (
        "Humidifier: %s" % (err_waterloss and "Water Loss(!!), " or "No Water Loss, ")
    )
    output = output + "Humidity: %3.1f%%" % humidity

    yield Metric("humidity", humidity)
    yield Result(
        state=State.CRIT if err_waterloss or err_global_status or err_emergency_op else State.OK,
        summary=output,
    )


def parse_carel_uniflair_cooling(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_carel_uniflair_cooling = SimpleSNMPSection(
    name="carel_uniflair_cooling",
    detect=DETECT_NEVER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1",
        oids=["1.31.0", "1.51.0", "1.67.0", "2.6.0"],
    ),
    parse_function=parse_carel_uniflair_cooling,
)
check_plugin_carel_uniflair_cooling = CheckPlugin(
    name="carel_uniflair_cooling",
    service_name="Carel uniflair cooling",
    discovery_function=inventory_carel_uniflair_cooling,
    check_function=check_carel_uniflair_cooling,
)
