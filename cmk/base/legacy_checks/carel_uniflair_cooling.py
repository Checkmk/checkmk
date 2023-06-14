#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.detection import DETECT_NEVER

# snmp_scan_function
# .1.3.6.1.2.1.1.4.0 = STRING: x.name@green-cooling.de < green-cooling match
# .1.3.6.1.2.1.1.5.0 = STRING: pCOWeb                    < pcoweb match
# .1.3.6.1.4.1.9839.1                                    < exists

# snmp_info
# .1.3.6.1.4.1.9839.2.1.1.31.0 = INTEGER: 0   < Waterloss
# .1.3.6.1.4.1.9839.2.1.1.51.0 = INTEGER: 1   < Global
# .1.3.6.1.4.1.9839.2.1.1.67.0 = INTEGER: 0   < Unit in Emergeny operation
# .1.3.6.1.4.1.9839.2.1.2.6.0 = INTEGER:  246 < Humidifier: Relative Humidity


def inventory_carel_uniflair_cooling(info):
    return [(None, None)]


def check_carel_uniflair_cooling(item, _no_params, info):
    waterloss, global_status, ermergency_op, humidity = info[0]

    err_waterloss = waterloss != "0"
    err_global_status = global_status != "1"
    err_emergency_op = ermergency_op != "0"
    humidity = float(humidity) / 10

    output = ""
    output = output + ("Global Status: %s" % (err_global_status and "Error(!!), " or "OK, "))
    output = output + (
        "Emergency Operation: %s" % (err_emergency_op and "Active(!!), " or "Inactive, ")
    )
    output = output + (
        "Humidifier: %s" % (err_waterloss and "Water Loss(!!), " or "No Water Loss, ")
    )
    output = output + "Humidity: %3.1f%%" % humidity

    perfdata = [("humidity", humidity)]
    if err_waterloss or err_global_status or err_emergency_op:
        return (2, output, perfdata)
    return (0, output, perfdata)


check_info["carel_uniflair_cooling"] = LegacyCheckDefinition(
    # All the OIDs of this checks seems to be wrong for the current version
    # of this device, so the detection is disbaled until we have better information
    detect=DETECT_NEVER,
    check_function=check_carel_uniflair_cooling,
    discovery_function=inventory_carel_uniflair_cooling,
    service_name="Carel uniflair cooling",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1",
        oids=["1.31.0", "1.51.0", "1.67.0", "2.6.0"],
    ),
)
