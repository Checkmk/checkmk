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


# .1.3.6.1.4.1.318.1.1.10.4.7.6.1


import enum
from typing import Mapping

from .agent_based_api.v1 import contains, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class FluidSensorState(enum.Enum):
    """Fluid sensor states according to APC PowerNet-MIB"""

    FLUIDLEAK = 1
    NOFLUID = 2
    UNKNOWN = 3


FluidSensorSection = Mapping[str, FluidSensorState]


def parse_apc_netbotz_fluid(string_table: StringTable) -> FluidSensorSection:
    return {
        f"{sensor_name} {module_idx}/{sensor_idx}": FluidSensorState(int(raw_sensor_state))
        for module_idx, sensor_idx, sensor_name, raw_sensor_state in string_table
    }


register.snmp_section(
    name="apc_netbotz_fluid",
    parse_function=parse_apc_netbotz_fluid,
    detect=contains(".1.3.6.1.2.1.1.1.0", "apc"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.4.7.6.1",
        oids=[
            "1",  # memFluidSensorStatusModuleIndex
            "2",  # memFluidSensorStatusSensorIndex
            "3",  # memFluidSensorStatusSensorName
            "5",  # memFluidSensorStatusSensorState 1 fluidleak 2 nofluid 3 unknown
        ],
    ),
)


def discover_apc_netbotz_fluid(section: FluidSensorSection) -> DiscoveryResult:
    for sensor in section:
        yield Service(item=sensor)


def check_apc_netbotz_fluid(item: str, section: FluidSensorSection) -> CheckResult:
    sensor = section.get(item)
    if sensor is None:
        return

    if sensor == FluidSensorState.FLUIDLEAK:
        yield Result(
            state=State.CRIT,
            summary="Leak detected",
        )
    elif sensor == FluidSensorState.NOFLUID:
        yield Result(
            state=State.OK,
            summary="No leak detected",
        )
    elif sensor == FluidSensorState.UNKNOWN:
        yield Result(
            state=State.UNKNOWN,
            summary="State Unknown",
        )


register.check_plugin(
    name="apc_netbotz_fluid",
    service_name="Fluid Detector %s",
    discovery_function=discover_apc_netbotz_fluid,
    check_function=check_apc_netbotz_fluid,
)
