#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# MIB can also be found in
# https://mibs.observium.org/mib/PowerNet-MIB/

# .1.3.6.1.2.1.1.1.0 APC Web/SNMP Management Card (MB:v4.1.0 PF:v6.8.2 PN:apc_hw05_aos_682.bin AF1:v6.8.0 AN1:apc_hw05_nb250_680.bin MN:NBRK0250 HR:HW05 SN: QA1943170153 MD:10/24/2019)
# .1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.318.1.3.8.5
# .1.3.6.1.2.1.1.3.0 420142900
# .1.3.6.1.2.1.1.4.0 Eleonore-IT
# .1.3.6.1.2.1.1.5.0 CA-ROU-ENV01
# .1.3.6.1.2.1.1.6.0 DC Rouyn-Noranda
# .1.3.6.1.2.1.1.7.0 72


# .1.3.6.1.4.1.318.1.1.10.4.7.2.1.3.0.3


import enum
from typing import Mapping

from .agent_based_api.v1 import contains, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class SmokeSensorState(enum.Enum):
    """Smoke sensor states according to APC PowerNet-MIB"""

    SMOKEDETECTED = 1
    NOSMOKE = 2
    UNKNOWN = 3


SmokeSensorSection = Mapping[str, SmokeSensorState]


def parse_apc_netbotz_smoke(string_table: StringTable) -> SmokeSensorSection:
    return {
        f"{sensor_name} {module_idx}/{sensor_idx}": SmokeSensorState(int(raw_sensor_state))
        for module_idx, sensor_idx, sensor_name, raw_sensor_state in string_table
    }


register.snmp_section(
    name="apc_netbotz_smoke",
    parse_function=parse_apc_netbotz_smoke,
    detect=contains(".1.3.6.1.2.1.1.1.0", "apc"),
    fetch=SNMPTree(
        # memSmokeSensorConfigEntry
        base=".1.3.6.1.4.1.318.1.1.10.4.7.2.1",
        oids=[
            "1",  # memSmokeSensorStatusModuleIndex
            "2",  # memSmokeSensorStatusSensorIndex
            "3",  # memSmokeSensorStatusSensorName
            "5",  # memSmokeSensorStatusSensorState 1 smokedetected 2 nosmoke 3 unknown
        ],
    ),
)


def discover_apc_netbotz_smoke(section: SmokeSensorSection) -> DiscoveryResult:
    for sensor in section:
        yield Service(item=sensor)


def check_apc_netbotz_smoke(item: str, section: SmokeSensorSection) -> CheckResult:
    sensor = section.get(item)
    if sensor is None:
        return

    if sensor == SmokeSensorState.SMOKEDETECTED:
        yield Result(
            state=State.CRIT,
            summary="Smoke detected",
        )
    elif sensor == SmokeSensorState.NOSMOKE:
        yield Result(
            state=State.OK,
            summary="No smoke detected",
        )
    elif sensor == SmokeSensorState.UNKNOWN:
        yield Result(
            state=State.UNKNOWN,
            summary="State Unknown",
        )


register.check_plugin(
    name="apc_netbotz_smoke",
    service_name="Smoke Detector %s",
    discovery_function=discover_apc_netbotz_smoke,
    check_function=check_apc_netbotz_smoke,
)
