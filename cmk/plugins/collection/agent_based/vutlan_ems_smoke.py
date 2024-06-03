#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# vutlan is not a typo!
# MIB can also be browsed on
# https://mibs.observium.org/mib/SKYCONTROL-SYSTEM-MIB/#


from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.vutlan import DETECT_VUTLAN_EMS


class SmokeSensor(NamedTuple):
    name: str
    state: int


SmokeSensorSection = Mapping[str, SmokeSensor]


def parse_vutlan_ems_smoke(string_table: StringTable) -> SmokeSensorSection:
    smoke_sensors = {}
    for sensor in string_table:
        if sensor[0].startswith("106"):
            # all OIDs 106xxx are smoke-related
            sensor_name = sensor[1]
            smoke_sensors[sensor_name] = SmokeSensor(name=sensor_name, state=int(sensor[2]))
    return smoke_sensors


snmp_section_vutlan_ems_smoke = SimpleSNMPSection(
    name="vutlan_ems_smoke",
    parse_function=parse_vutlan_ems_smoke,
    detect=DETECT_VUTLAN_EMS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.39052.1.3.1",
        oids=[
            OIDEnd(),
            "7",  # vutlan.mib::ctlUnitElementName (can be user-defined)
            "9",  # vutlan.mib::ctlUnitElementValue
        ],
    ),
)


def discover_vutlan_ems_smoke(section: SmokeSensorSection) -> DiscoveryResult:
    for sensor in section.values():
        yield Service(item=sensor.name)


def check_vutlan_ems_smoke(item: str, section: SmokeSensorSection) -> CheckResult:
    sensor = section.get(item)
    if sensor is None:
        return

    if sensor.state:
        yield Result(
            state=State.CRIT,
            summary="Smoke detected",
        )
        return

    yield Result(
        state=State.OK,
        summary="No smoke detected",
    )


check_plugin_vutlan_ems_smoke = CheckPlugin(
    name="vutlan_ems_smoke",
    service_name="Smoke Detector %s",
    discovery_function=discover_vutlan_ems_smoke,
    check_function=check_vutlan_ems_smoke,
)
