#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import equals, LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree


def inventory_rms200_temp(info):
    for line in info:
        if line[2] != "-27300":
            yield (line[0], {})
        # otherwise no sensor is connected


def check_rms200_temp(item, params, info):
    for line in info:
        if line[0] == item:
            status, infotext, perfdata = check_temperature(
                float(line[2]) / 100, params, "rms200_temp_%s" % item
            )
            infotext += " (%s)" % line[1]  # Name from SNMP data
            return status, infotext, perfdata
    return None


check_info["rms200_temp"] = LegacyCheckDefinition(
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1909.13"),
    check_function=check_rms200_temp,
    discovery_function=inventory_rms200_temp,
    service_name="Temperature %s ",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1909.13.1.1.1",
        oids=["1", "2", "5"],
    ),
    check_default_parameters={"levels": (25.0, 28.0)},
)
