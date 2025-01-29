#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import CheckPlugin, SimpleSNMPSection, SNMPTree
from cmk.plugins.lib.akcp import DETECT_AKCP_EXP
from cmk.plugins.lib.akcp_sensor import (
    check_akcp_sensor_drycontact,
    inventory_akcp_sensor_no_params,
    parse_akcp_sensor,
)

# Example for contents of info
#           description            state  online  critical_desc  normal_desc
# ["Diesel1 Generatorbetrieb",      "2",   "1",        "An",         "Aus"]]

snmp_section_akcp_exp_drycontact = SimpleSNMPSection(
    name="akcp_exp_drycontact",
    parse_function=parse_akcp_sensor,
    detect=DETECT_AKCP_EXP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.4.1",
        oids=["2", "6", "46", "48", "8"],
    ),
)


check_plugin_akcp_exp_drycontact = CheckPlugin(
    name="akcp_exp_drycontact",
    service_name="Dry Contact %s",
    check_function=check_akcp_sensor_drycontact,
    discovery_function=inventory_akcp_sensor_no_params,
)
