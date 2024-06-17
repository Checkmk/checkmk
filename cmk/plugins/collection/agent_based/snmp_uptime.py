#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree
from cmk.plugins.lib import detection
from cmk.plugins.lib.uptime import parse_snmp_uptime

snmp_section_snmp_uptime = SimpleSNMPSection(
    name="snmp_uptime",
    parsed_section_name="uptime",
    parse_function=parse_snmp_uptime,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1",
        oids=[
            # On Linux appliances: .1.3.6.1.2.1.1.3.0    means uptime of snmpd
            #                      .1.3.6.1.2.1.25.1.1.0 means system uptime
            "1.3",  # DISMAN-EVENT-MIB::sysUpTime
            "25.1.1",  # HOST-RESOURCES-MIB::hrSystemUptime
        ],
    ),
    detect=detection.HAS_SYSDESC,
)
