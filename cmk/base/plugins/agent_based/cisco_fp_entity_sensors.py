#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# SNMPv2-MIB::sysDescr.0 = STRING: Cisco Firepower FPR-1140 Security Appliance, System Version 2.7(1.115)
#
# .1.3.6.1.4.1.9.9.91.1.1.1.1.1.47 = INTEGER: 10                                 # entSensorType (rpm)
# .1.3.6.1.4.1.9.9.91.1.1.1.1.2.47 = INTEGER: 9                                  # entSensorScale (units)
# .1.3.6.1.4.1.9.9.91.1.1.1.1.3.47 = INTEGER: 0                                  # entSensorPrecision
# .1.3.6.1.4.1.9.9.91.1.1.1.1.4.47 = INTEGER: 2820                               # entSensorValue
# .1.3.6.1.4.1.9.9.91.1.1.1.1.5.47 = INTEGER: 1                                  # entSensorStatus (ok)
# .1.3.6.1.4.1.9.9.91.1.1.1.1.6.47 = Timeticks: (397951199) 46 days, 1:25:11.99  # entSensorValueTimeStamp
# .1.3.6.1.4.1.9.9.91.1.1.1.1.7.47 = INTEGER: 60                                 # entSensorValueUpdateRate (seconds)
# .1.3.6.1.4.1.9.9.91.1.1.1.1.8.47 = INTEGER: 10            # entSensorMeasuredEntity -> entPhysicalIndex -> no match
#
# CISCO-ENTITY-SENSOR-MIB::entSensorType.47 = INTEGER: rpm(10)
# CISCO-ENTITY-SENSOR-MIB::entSensorScale.47 = INTEGER: units(9)
# CISCO-ENTITY-SENSOR-MIB::entSensorPrecision.47 = INTEGER: 0
# CISCO-ENTITY-SENSOR-MIB::entSensorValue.47 = INTEGER: 2820
# CISCO-ENTITY-SENSOR-MIB::entSensorStatus.47 = INTEGER: ok(1)
# CISCO-ENTITY-SENSOR-MIB::entSensorValueTimeStamp.47 = Timeticks: (397951199) 46 days, 1:25:11.99
# CISCO-ENTITY-SENSOR-MIB::entSensorValueUpdateRate.47 = INTEGER: 60 seconds
# CISCO-ENTITY-SENSOR-MIB::entSensorMeasuredEntity.47 = INTEGER: 10
#
# entPhysicalIndex
# .1.3.6.1.2.1.47.1.1.1.1.7.9 = STRING: 'CHASSIS-1'
# .1.3.6.1.2.1.47.1.1.1.1.7.10 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.11 = STRING: 'FAN-1'
# .1.3.6.1.2.1.47.1.1.1.1.7.12 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.13 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.14 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.15 = STRING: 'PSU-1'
# .1.3.6.1.2.1.47.1.1.1.1.7.16 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.17 = STRING: 'MEMORY-1'
# .1.3.6.1.2.1.47.1.1.1.1.7.18 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.19 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.20 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.21 = STRING: 'SSD-1'
# .1.3.6.1.2.1.47.1.1.1.1.7.22 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.23 = STRING: 'CPU-1'
# .1.3.6.1.2.1.47.1.1.1.1.7.24 = ''
# .1.3.6.1.2.1.47.1.1.1.1.7.25 = ''

from typing import List

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    contains,
    OIDEnd,
    register,
    SNMPTree,
    startswith,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils import entity_sensors as utils
from cmk.base.plugins.agent_based.utils.entity_sensors import EntitySensorSection, OIDSysDescr


def parse_cisco_fp_entity_sensors(string_table: List[StringTable]) -> EntitySensorSection:
    # do not add undefined and temperature (duplicate with cisco_temperature) sensors
    return utils.parse_entity_sensors(
        string_table,
        sensor_types_ignore={"0", "8"},
    )


register.snmp_section(
    name="cisco_fp_entity_sensors",
    supersedes=["entity_sensors"],
    detect=all_of(
        startswith(OIDSysDescr, "Cisco Firepower"),
        contains(OIDSysDescr, "security appliance"),
    ),
    parsed_section_name="entity_sensors",
    parse_function=parse_cisco_fp_entity_sensors,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",  # ENTITY-MIB
            oids=[
                OIDEnd(),
                "7",  # ENTITY-MIB::entPhysicalName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.91.1.1.1.1",  # CISCO-ENTITY-SENSOR-MIB
            oids=[
                OIDEnd(),
                "1",  # entPhySensorType
                "2",  # entPhySensorScale
                "4",  # entPhySensorValue
                "5",  # entPhySensorOperStatus
                "6",  # entPhySensorUnitsDisplay
            ],
        ),
    ],
)
