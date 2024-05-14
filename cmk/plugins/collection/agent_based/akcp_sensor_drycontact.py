#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    not_exists,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
)
from cmk.plugins.lib.akcp import DETEC_AKCP_SP2PLUS
from cmk.plugins.lib.akcp_sensor import (
    check_akcp_sensor_drycontact,
    inventory_akcp_sensor_no_params,
    parse_akcp_sensor,
)

snmp_section_akcp_sensor_drycontact = SimpleSNMPSection(
    name="akcp_sensor_drycontact",
    parse_function=parse_akcp_sensor,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3854.1"), not_exists(".1.3.6.1.4.1.3854.2.*")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.1.2.2.1.18.1",
        oids=[
            "1",  # hhmsSensorArraySwitchDescription
            "3",  # hhmsSensorArraySwitchStatus
            "5",  # hhmsSensorArraySwitchGoOnline (1: online, 2: offline)
        ],
    ),
)


snmp_section_akcp_sensor2plus_drycontact = SimpleSNMPSection(
    name="akcp_sensor2plus_drycontact",
    parse_function=parse_akcp_sensor,
    parsed_section_name="akcp_sensor_drycontact",
    detect=DETEC_AKCP_SP2PLUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.3.5.4.1",
        oids=[
            "2",  # drycontactDescription
            "6",  # drycontactStatus
            "8",  # drycontactGoOffline (1: online, 2: offline)
        ],
    ),
)


check_plugin_akcp_sensor_drycontact = CheckPlugin(
    name="akcp_sensor_drycontact",
    service_name="Dry Contact %s",
    check_function=check_akcp_sensor_drycontact,
    discovery_function=inventory_akcp_sensor_no_params,
)
