#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.lib.akcp import DETECT_AKCP_EXP
from cmk.plugins.lib.akcp_sensor import (
    AKCP_TEMP_CHECK_DEFAULT_PARAMETERS,
    check_akcp_sensor_temp,
    inventory_akcp_sensor_temp,
    parse_akcp_sensor,
)

from .agent_based_api.v1 import register, SNMPTree

# Example for contents of info
#           description         degree unit status low_crit low_warn high_warn high_crit degreeraw online
# ["Port 8 Temperatur CL Lager", "20", "C",   "5",   "10",    "20",    "30",     "40",      "0",     1]

register.snmp_section(
    name="akcp_exp_temp",
    parse_function=parse_akcp_sensor,
    detect=DETECT_AKCP_EXP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.2.1",
        oids=["2", "4", "5", "6", "9", "10", "11", "12", "19", "8"],
    ),
)


register.check_plugin(
    name="akcp_exp_temp",
    service_name="Temperature %s",
    check_function=check_akcp_sensor_temp,
    discovery_function=inventory_akcp_sensor_temp,
    check_ruleset_name="temperature",
    check_default_parameters=AKCP_TEMP_CHECK_DEFAULT_PARAMETERS,
)
