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
    StringTable,
)
from cmk.plugins.checkpoint.lib import DETECT, SENSOR_STATUS_TO_CMK_STATUS


def parse_checkpoint_voltage(string_table: StringTable) -> StringTable:
    return string_table


def discover_checkpoint_voltage(section: StringTable) -> DiscoveryResult:
    for name, _value, _unit, _dev_status in section:
        yield Service(item=name)


def check_checkpoint_voltage(item: str, section: StringTable) -> CheckResult:
    for name, value, unit, dev_status in section:
        if name == item:
            state, state_readable = SENSOR_STATUS_TO_CMK_STATUS[dev_status]
            yield Result(state=state, summary=f"Status: {state_readable}, {value} {unit}")
            return


snmp_section_checkpoint_voltage = SimpleSNMPSection(
    name="checkpoint_voltage",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.8.3.1",
        oids=["2", "3", "4", "6"],
    ),
    parse_function=parse_checkpoint_voltage,
)


check_plugin_checkpoint_voltage = CheckPlugin(
    name="checkpoint_voltage",
    service_name="Voltage %s",
    discovery_function=discover_checkpoint_voltage,
    check_function=check_checkpoint_voltage,
)
