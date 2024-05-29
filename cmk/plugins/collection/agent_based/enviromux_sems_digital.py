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
)
from cmk.plugins.lib.enviromux import (
    DETECT_ENVIROMUX_SEMS,
    EnviromuxDigitalSection,
    parse_enviromux_digital,
)

snmp_section_enviromux_sems_digital = SimpleSNMPSection(
    name="enviromux_sems_digital",
    parse_function=parse_enviromux_digital,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3699.1.1.2.1.6.1.1",
        oids=[
            "1",  # digIntputIndex
            "2",  # digIntputDescription
            "5",  # digIntputValue
            "6",  # digIntputNormalValue
        ],
    ),
    detect=DETECT_ENVIROMUX_SEMS,
)


def discover_enviromux_sems_digital(section: EnviromuxDigitalSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_enviromux_sems_digital(
    item: str,
    section: EnviromuxDigitalSection,
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    if sensor.value == "unknown":
        yield Result(
            state=State.UNKNOWN,
            summary="Sensor value is unknown",
        )
        return

    if sensor.value == sensor.normal_value:
        yield Result(
            state=State.OK,
            summary=f"Sensor Value is normal: {sensor.value}",
        )
        return

    yield Result(
        state=State.CRIT,
        summary=f"Sensor Value is not normal: {sensor.value} . It should be: {sensor.normal_value}",
    )


check_plugin_enviromux_sems_digital = CheckPlugin(
    name="enviromux_sems_digital",
    service_name="Digital Sensor: %s",
    discovery_function=discover_enviromux_sems_digital,
    check_function=check_enviromux_sems_digital,
)
