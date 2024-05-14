#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, SimpleSNMPSection, SNMPTree
from cmk.plugins.lib.akcp import DETECT_AKCP_EXP
from cmk.plugins.lib.akcp_sensor import (
    AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS,
    check_akcp_humidity,
    inventory_akcp_humidity,
    parse_akcp_sensor,
)

# Example for contents of info
#           description         percent  status  online
# ["Port 8 Feuchte USV Raum A",  "38",    "5",    "1"]


snmp_section_akcp_exp_humidity = SimpleSNMPSection(
    name="akcp_exp_humidity",
    parse_function=parse_akcp_sensor,
    detect=DETECT_AKCP_EXP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.3.1",
        oids=["2", "4", "6", "8"],
    ),
)


check_plugin_akcp_exp_humidity = CheckPlugin(
    name="akcp_exp_humidity",
    service_name="Humidity %s",
    check_function=check_akcp_humidity,
    discovery_function=inventory_akcp_humidity,
    check_ruleset_name="humidity",
    check_default_parameters=AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS,
)
