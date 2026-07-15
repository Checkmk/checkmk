#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import enum
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    not_exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.akcp.lib import DETEC_AKCP_SP2PLUS, DETECT_AKCP_EXP


class SensorStatus(enum.Enum):
    # Status values as defined in SPAGENT-MIB
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_WARNING = "3"
    HIGH_CRITICAL = "4"
    LOW_WARNING = "5"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"
    OUTPUT_LOW = "8"
    OUTPUT_HIGH = "9"


def _check_status(
    status: SensorStatus,
    online: bool,
    normal_description: str,
    critical_description: str,
) -> CheckResult:
    # States which are not configurable by user as they are defined in SPAGENT-MIB
    state_names = {
        SensorStatus.NO_STATUS: "no status",
        SensorStatus.SENSOR_ERROR: "sensor error",
        SensorStatus.OUTPUT_LOW: "output low",
        SensorStatus.OUTPUT_HIGH: "output high",
    }

    if not online:
        yield Result(state=State.CRIT, summary="Sensor is offline")
    elif status is SensorStatus.NORMAL:
        yield Result(state=State.OK, summary=normal_description)
    elif status in (SensorStatus.HIGH_CRITICAL, SensorStatus.LOW_CRITICAL):
        yield Result(state=State.CRIT, summary=critical_description)
    else:
        yield Result(state=State.CRIT, summary=state_names[status])


@dataclass(frozen=True, kw_only=True)
class DrycontactSensor:
    status: SensorStatus
    online: bool


DrycontactSection = Mapping[str, DrycontactSensor]


def parse_akcp_sensor_drycontact(string_table: StringTable) -> DrycontactSection:
    return {
        description: DrycontactSensor(status=SensorStatus(status), online=online == "1")
        for description, status, online in string_table
    }


snmp_section_akcp_sensor_drycontact = SimpleSNMPSection(
    name="akcp_sensor_drycontact",
    parse_function=parse_akcp_sensor_drycontact,
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
    parse_function=parse_akcp_sensor_drycontact,
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


def discover_akcp_sensor_drycontact(section: DrycontactSection) -> DiscoveryResult:
    for description, sensor in section.items():
        if sensor.online:
            yield Service(item=description)


def check_akcp_sensor_drycontact(item: str, section: DrycontactSection) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    yield from _check_status(sensor.status, sensor.online, "Drycontact OK", "Drycontact on Error")


check_plugin_akcp_sensor_drycontact = CheckPlugin(
    name="akcp_sensor_drycontact",
    service_name="Dry Contact %s",
    check_function=check_akcp_sensor_drycontact,
    discovery_function=discover_akcp_sensor_drycontact,
)


@dataclass(frozen=True, kw_only=True)
class ExpDrycontactSensor:
    status: SensorStatus
    online: bool
    normal_description: str
    critical_description: str


ExpDrycontactSection = Mapping[str, ExpDrycontactSensor]


def parse_akcp_exp_drycontact(string_table: StringTable) -> ExpDrycontactSection:
    return {
        description: ExpDrycontactSensor(
            status=SensorStatus(status),
            online=online == "1",
            normal_description=normal_description,
            critical_description=critical_description,
        )
        for description, status, critical_description, normal_description, online in string_table
    }


snmp_section_akcp_exp_drycontact = SimpleSNMPSection(
    name="akcp_exp_drycontact",
    parse_function=parse_akcp_exp_drycontact,
    detect=DETECT_AKCP_EXP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.4.1",
        oids=[
            "2",  # sensorDryContactDescription
            "6",  # sensorDryContactStatus
            "46",  # sensorDryContactCriticalDesc
            "48",  # sensorDryContactNormalDesc
            "8",  # sensorDryContactGoOffline (1: online, 2: offline)
        ],
    ),
)


def discover_akcp_exp_drycontact(section: ExpDrycontactSection) -> DiscoveryResult:
    for description, sensor in section.items():
        if sensor.online:
            yield Service(item=description)


def check_akcp_exp_drycontact(item: str, section: ExpDrycontactSection) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    yield from _check_status(
        sensor.status,
        sensor.online,
        sensor.normal_description,
        sensor.critical_description,
    )


check_plugin_akcp_exp_drycontact = CheckPlugin(
    name="akcp_exp_drycontact",
    service_name="Dry Contact %s",
    check_function=check_akcp_exp_drycontact,
    discovery_function=discover_akcp_exp_drycontact,
)
