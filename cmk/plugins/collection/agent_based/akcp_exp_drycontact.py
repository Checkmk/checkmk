#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import CheckPlugin, SimpleSNMPSection, SNMPTree
from cmk.plugins.akcp.lib import DETECT_AKCP_EXP
from cmk.plugins.akcp.lib_sensor import (
    check_akcp_exp_drycontact,
    discover_akcp_exp_drycontact,
    parse_akcp_exp_drycontact,
)

snmp_section_akcp_exp_drycontact = SimpleSNMPSection(
    name="akcp_exp_drycontact",
    parse_function=parse_akcp_exp_drycontact,
    detect=DETECT_AKCP_EXP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.4.1",
        oids=[
            "2",  # sensorDryContactDescription
            "6",  # sensorDryContactStatus
            "46",  # sensorDryContactCriticalDesc
            "48",  # sensorDryContactNormalDesc
            "8",  # sensorDryContactGoOffline (1: online, 2: offline)
        ],
    ),
)


check_plugin_akcp_exp_drycontact = CheckPlugin(
    name="akcp_exp_drycontact",
    service_name="Dry Contact %s",
    check_function=check_akcp_exp_drycontact,
    discovery_function=discover_akcp_exp_drycontact,
)
