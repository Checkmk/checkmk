#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    any_of,
    exists,
    not_exists,
    SNMPTree,
    startswith,
)

# We fetch the following columns from SNMP:
# 13: name of the temperature sensor (used as item)
# 11: current temperature in C
# 6:  warning level
# 8:  critical level


def inventory_fsc_temp(info):
    for line in info:
        # Ignore non-connected sensors
        if int(line[1]) < 500:
            yield (line[0], None)


def check_fsc_temp(item, params, info):
    for name, rawtemp, warn, crit in info:
        if name == item:
            temp = int(rawtemp)
            if temp in {-1, 4294967295}:
                return 3, "Sensor or component missing"

            return check_temperature(
                temp, params, "fsc_temp_%s" % item, dev_levels=(int(warn), int(crit))
            )
    return None


check_info["fsc_temp"] = LegacyCheckDefinition(
    detect=all_of(
        all_of(
            any_of(
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
            ),
            exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
        ),
        not_exists(".1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.*"),
    ),
    discovery_function=inventory_fsc_temp,
    check_function=check_fsc_temp,
    service_name="Temperature %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.5.2.1.1",
        oids=["13", "11", "6", "8"],
    ),
    check_ruleset_name="temperature",
)
