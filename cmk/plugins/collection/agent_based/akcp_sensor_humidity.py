#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Example for contents of info
#      description       percent  status  online
# ["Humdity1 Description", "0",    "0",    "2"]


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
    AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS,
    check_akcp_humidity,
    inventory_akcp_humidity,
    parse_akcp_sensor,
)

snmp_section_akcp_sensor_humidity = SimpleSNMPSection(
    name="akcp_sensor_humidity",
    parse_function=parse_akcp_sensor,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3854.1"), not_exists(".1.3.6.1.4.1.3854.2.*")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.1.2.2.1.17.1",
        oids=[
            "1",  # hhmsSensorArrayHumidityDescription
            "3",  # hhmsSensorArrayHumidityPercent
            "4",  # hhmsSensorArrayHumidityStatus
            "5",  # hhmsSensorArrayHumidityOnline (1: online, 2: offline)
        ],
    ),
)


snmp_section_akcp_sensor2plus_humidity = SimpleSNMPSection(
    name="akcp_sensor2plus_humidity",
    parse_function=parse_akcp_sensor,
    parsed_section_name="akcp_sensor_humidity",
    detect=DETEC_AKCP_SP2PLUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.3.5.3.1",
        oids=[
            "2",  # humidityDescription
            "4",  # humidityPercent
            "6",  # humidityStatus
            "8",  # humidityGoOffline (1: online, 2: offline)
        ],
    ),
)


check_plugin_akcp_sensor_humidity = CheckPlugin(
    name="akcp_sensor_humidity",
    service_name="Humidity %s",
    check_function=check_akcp_humidity,
    discovery_function=inventory_akcp_humidity,
    check_ruleset_name="humidity",
    check_default_parameters=AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS,
)
