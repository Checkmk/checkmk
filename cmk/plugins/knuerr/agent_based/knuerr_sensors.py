#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.knuerr.lib import DETECT_KNUERR


def discover_knuerr_sensors(section: StringTable) -> DiscoveryResult:
    for sensor, _state in section:
        if sensor:
            yield Service(item=sensor)


def check_knuerr_sensors(item: str, section: StringTable) -> CheckResult:
    for sensor, state in section:
        if sensor == item:
            if state != "0":
                yield Result(state=State.CRIT, summary="Sensor triggered")
            else:
                yield Result(state=State.OK, summary="Sensor not triggered")
            return
    yield Result(state=State.UNKNOWN, summary="Sensor no longer found")


def parse_knuerr_sensors(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_knuerr_sensors = SimpleSNMPSection(
    name="knuerr_sensors",
    detect=DETECT_KNUERR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3711.15.1.1.2",
        oids=["1", "5"],
    ),
    parse_function=parse_knuerr_sensors,
)


check_plugin_knuerr_sensors = CheckPlugin(
    name="knuerr_sensors",
    service_name="Sensor %s",
    discovery_function=discover_knuerr_sensors,
    check_function=check_knuerr_sensors,
)
