#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from .agent_based_api.v1 import register, SNMPTree
from .utils.akcp import DETEC_AKCP_SP2PLUS, DETECT_AKCP_EXP
from .utils.akcp_sensor import (
    check_akcp_sensor_relay,
    inventory_akcp_sensor_no_params,
    parse_akcp_sensor,
)

# Example for contents of info
#           description                 state  online
# ["Port 4 Rauchmelder USV Raum A",      "2",   "1"]

register.snmp_section(
    name="akcp_exp_smoke",
    parse_function=parse_akcp_sensor,
    detect=DETECT_AKCP_EXP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.14.1",
        oids=[
            "2",  # sensorSmokeDescription
            "6",  # sensorSmokeStatus
            "8",  # sensorSmokeGoOffline (1: online, 2: offline)
        ],
    ),
)


register.snmp_section(
    name="akcp_sensor2plus_smoke",
    parsed_section_name="akcp_exp_smoke",
    parse_function=parse_akcp_sensor,
    detect=DETEC_AKCP_SP2PLUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.3.5.14.1",
        oids=[
            "2",  # smokeDescription
            "6",  # smokeStatus
            "8",  # smokeGoOffline (1: online, 2: offline)
        ],
    ),
)


register.check_plugin(
    name="akcp_exp_smoke",
    service_name="Smoke %s",
    check_function=check_akcp_sensor_relay,
    discovery_function=inventory_akcp_sensor_no_params,
)
