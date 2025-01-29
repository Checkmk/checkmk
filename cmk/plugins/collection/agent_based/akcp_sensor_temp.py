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
    AKCP_TEMP_CHECK_DEFAULT_PARAMETERS,
    check_akcp_sensor_temp,
    inventory_akcp_sensor_temp,
    parse_akcp_sensor,
)

# Example for contents of info
#   description     degree  unit status low_crit low_warn high_warn  high_crit degreeraw online
# ["HGS-RZ1TEMP-TH1", "22", "1",   "2",   "18",   "20",    "25",      "28",      "",     "1"]

snmp_section_akcp_sensor_temp = SimpleSNMPSection(
    name="akcp_sensor_temp",
    parse_function=parse_akcp_sensor,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3854.1"), not_exists(".1.3.6.1.4.1.3854.2.*")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.1.2.2.1.16.1",
        oids=[
            "1",  # hhmsSensorArrayTempDescription
            "3",  # hhmsSensorArrayTempDegree
            "12",  # hhmsSensorArrayTempDegreeType
            "4",  # hhmsSensorArrayTempStatus
            "10",  # hhmsSensorArrayTempLowCritical
            "9",  # hhmsSensorArrayTempLowWarning
            "7",  # hhmsSensorArrayTempHighWarning
            "8",  # hhmsSensorArrayTempHighCritical
            "14",  # hhmsSensorArrayTempTestStatus
            "5",  # hhmsSensorArrayTempOnline (1: online, 2: offline)
        ],
    ),
)


snmp_section_akcp_sensor2plus_temp = SimpleSNMPSection(
    name="akcp_sensor2plus_temp",
    parse_function=parse_akcp_sensor,
    parsed_section_name="akcp_sensor_temp",
    detect=DETEC_AKCP_SP2PLUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.3.5.2.1",
        oids=[
            "2",  # temperatureDescription
            "4",  # temperatureDegree
            "5",  # temperatureUnit
            "6",  # temperatureStatus
            "9",  # temperatureLowCritical
            "10",  # temperatureLowWarning
            "11",  # temperatureHighWarning
            "12",  # temperatureHighCritical
            "20",  # temperatureRaw
            "8",  # temperatureGoOffline (1: online, 2: offline)
        ],
    ),
)


check_plugin_akcp_sensor_temp = CheckPlugin(
    name="akcp_sensor_temp",
    service_name="Temperature %s",
    check_function=check_akcp_sensor_temp,
    discovery_function=inventory_akcp_sensor_temp,
    check_ruleset_name="temperature",
    check_default_parameters=AKCP_TEMP_CHECK_DEFAULT_PARAMETERS,
)
