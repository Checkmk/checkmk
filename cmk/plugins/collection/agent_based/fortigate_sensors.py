#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

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
from cmk.plugins.lib.fortinet import DETECT_FORTIGATE


class FortigateSensors(NamedTuple):
    total: int
    critical_sensors: tuple[str, ...]

    @property
    def critical(self) -> int:
        return len(self.critical_sensors)

    @property
    def ok(self) -> int:
        return self.total - self.critical


def parse_fortigate_sensors(string_table: StringTable) -> FortigateSensors:
    # We assume that sensors with value "0" are not connected and may be ignored.
    # The related MIB includes no other hint for that.
    return FortigateSensors(
        total=sum(value != "0" for _name, value, status in string_table),
        critical_sensors=tuple(
            name for name, value, status in string_table if value != "0" and status == "1"
        ),
    )


def discover_fortigate_sensors(section: FortigateSensors) -> DiscoveryResult:
    if section.total >= 1:
        yield Service()


def check_fortigate_sensors(section: FortigateSensors) -> CheckResult:
    yield Result(state=State.OK, summary=f"{section.total} sensors")
    yield Result(state=State.OK, summary=f"{section.ok} OK")
    yield Result(state=State.OK, summary=f"{section.critical} with alarm")

    for sensor in section.critical_sensors:
        yield Result(state=State.CRIT, summary=f"{sensor}")


snmp_section_fortigate_sensors = SimpleSNMPSection(
    name="fortigate_sensors",
    detect=DETECT_FORTIGATE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.4.3.2.1",
        oids=[
            "2",  # FORTINET-FORTIGATE-MIB::fgHwSensorEntName
            "3",  # FORTINET-FORTIGATE-MIB::fgHwSensorEntValue
            "4",  # FORTINET-FORTIGATE-MIB::fgHwSensorEntAlarmStatus
        ],
    ),
    parse_function=parse_fortigate_sensors,
)


check_plugin_fortigate_sensors = CheckPlugin(
    name="fortigate_sensors",
    service_name="Sensor Summary",
    discovery_function=discover_fortigate_sensors,
    check_function=check_fortigate_sensors,
)
