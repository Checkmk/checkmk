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
    IgnoreResults,
    not_exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.akcp import DETEC_AKCP_SP2PLUS, DETECT_AKCP_EXP
from cmk.plugins.lib.akcp_sensor import filter_broken_rows


class SensorProbeSwitchStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorProbeSwitchStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highCritical(4),
    #           lowCritical(6),
    #           sensorError(7),
    #           relayOn(8),
    #           relayOff(9)
    #        }
    # Decodes .1.3.6.1.4.1.3854.1.2.2.1.18.1.3
    # "0" is not defined in the MIB, but real devices have been observed to
    # report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_CRITICAL = "4"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"
    RELAY_ON = "8"
    RELAY_OFF = "9"


class SensorDryContactStatus(enum.Enum):
    # SPAGENT-MIB:
    #     sensorDryContactStatus OBJECT-TYPE
    #        SYNTAX  INTEGER {
    #           noStatus(1),
    #           normal(2),
    #           highCritical(4),
    #           lowCritical(6),
    #           sensorError(7),
    #           outputLow(8),
    #           outputHigh(9)
    #        }
    #     drycontactStatus OBJECT-TYPE
    #        SYNTAX  INTEGER { <identical to sensorDryContactStatus above> }
    # Decodes .1.3.6.1.4.1.3854.2.3.4.1.6 (sensorDryContactStatus)
    # and .1.3.6.1.4.1.3854.3.5.4.1.6 (plusSeries drycontactStatus)
    # "0" is not defined in the MIB, but real devices have been observed to
    # report it, both online and offline.
    NO_VALUE = "0"
    NO_STATUS = "1"
    NORMAL = "2"
    HIGH_CRITICAL = "4"
    LOW_CRITICAL = "6"
    SENSOR_ERROR = "7"
    OUTPUT_LOW = "8"
    OUTPUT_HIGH = "9"


def _check_status(
    status: SensorDryContactStatus | SensorProbeSwitchStatus,
    online: bool,
    normal_description: str,
    critical_description: str,
) -> CheckResult:
    if status in (SensorDryContactStatus.NO_VALUE, SensorProbeSwitchStatus.NO_VALUE):
        yield IgnoreResults("Sensor did not report a status")
        return

    state_names = {
        SensorDryContactStatus.NO_STATUS: "no status",
        SensorDryContactStatus.SENSOR_ERROR: "sensor error",
        SensorDryContactStatus.OUTPUT_LOW: "output low",
        SensorDryContactStatus.OUTPUT_HIGH: "output high",
        SensorProbeSwitchStatus.NO_STATUS: "no status",
        SensorProbeSwitchStatus.SENSOR_ERROR: "sensor error",
        SensorProbeSwitchStatus.RELAY_ON: "output low",
        SensorProbeSwitchStatus.RELAY_OFF: "output high",
    }

    if not online:
        yield Result(state=State.CRIT, summary="Sensor is offline")
    elif status in (SensorDryContactStatus.NORMAL, SensorProbeSwitchStatus.NORMAL):
        yield Result(state=State.OK, summary=normal_description)
    elif status in (
        SensorDryContactStatus.HIGH_CRITICAL,
        SensorDryContactStatus.LOW_CRITICAL,
        SensorProbeSwitchStatus.HIGH_CRITICAL,
        SensorProbeSwitchStatus.LOW_CRITICAL,
    ):
        yield Result(state=State.CRIT, summary=critical_description)
    else:
        yield Result(state=State.CRIT, summary=state_names[status])


@dataclass(frozen=True, kw_only=True)
class ProbeSwitchSensor:
    status: SensorProbeSwitchStatus
    online: bool


@dataclass(frozen=True, kw_only=True)
class DrycontactSensor:
    status: SensorDryContactStatus
    online: bool


DrycontactSection = Mapping[str, ProbeSwitchSensor | None] | Mapping[str, DrycontactSensor | None]


def parse_akcp_sensor_drycontact(
    string_table: StringTable,
) -> Mapping[str, ProbeSwitchSensor | None]:
    rows, broken = filter_broken_rows(string_table, required_columns=(0, 1, 2))
    return {
        **dict.fromkeys(broken),
        **{
            description: ProbeSwitchSensor(
                status=SensorProbeSwitchStatus(status), online=online == "1"
            )
            for description, status, online in rows
        },
    }


def parse_akcp_sensor2plus_drycontact(
    string_table: StringTable,
) -> Mapping[str, DrycontactSensor | None]:
    rows, broken = filter_broken_rows(string_table, required_columns=(0, 1, 2))
    return {
        **dict.fromkeys(broken),
        **{
            description: DrycontactSensor(
                status=SensorDryContactStatus(status), online=online == "1"
            )
            for description, status, online in rows
        },
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
            "4",  # hhmsSensorArraySwitchOnline (1: online, 2: offline)
        ],
    ),
)


snmp_section_akcp_sensor2plus_drycontact = SimpleSNMPSection(
    name="akcp_sensor2plus_drycontact",
    parse_function=parse_akcp_sensor2plus_drycontact,
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
        if sensor is None or sensor.online:
            yield Service(item=description)


def check_akcp_sensor_drycontact(item: str, section: DrycontactSection) -> CheckResult:
    if item not in section:
        return
    if (sensor := section[item]) is None:
        yield IgnoreResults("Sensor reported corrupted values")
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
    status: SensorDryContactStatus
    online: bool
    normal_description: str
    critical_description: str


ExpDrycontactSection = Mapping[str, ExpDrycontactSensor | None]


def parse_akcp_exp_drycontact(string_table: StringTable) -> ExpDrycontactSection:
    # Unlike the other drycontact tables, this one has the online field last.
    rows, broken = filter_broken_rows(string_table, required_columns=(0, 1, 4))
    return {
        **dict.fromkeys(broken),
        **{
            description: ExpDrycontactSensor(
                status=SensorDryContactStatus(status),
                online=online == "1",
                normal_description=normal_description,
                critical_description=critical_description,
            )
            for description, status, critical_description, normal_description, online in rows
        },
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
        if sensor is None or sensor.online:
            yield Service(item=description)


def check_akcp_exp_drycontact(item: str, section: ExpDrycontactSection) -> CheckResult:
    if item not in section:
        return
    if (sensor := section[item]) is None:
        yield IgnoreResults("Sensor reported corrupted values")
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
