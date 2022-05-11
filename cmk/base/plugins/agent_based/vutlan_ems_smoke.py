#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# vutlan is not a typo!
# MIB can also be browsed on
# https://mibs.observium.org/mib/SKYCONTROL-SYSTEM-MIB/#


from typing import Mapping, NamedTuple

from .agent_based_api.v1 import contains, OIDEnd, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


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


register.snmp_section(
    name="vutlan_ems_smoke",
    parse_function=parse_vutlan_ems_smoke,
    detect=contains(".1.3.6.1.2.1.1.1.0", "vutlan ems"),
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


register.check_plugin(
    name="vutlan_ems_smoke",
    service_name="Smoke Detector %s",
    discovery_function=discover_vutlan_ems_smoke,
    check_function=check_vutlan_ems_smoke,
)
