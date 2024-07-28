#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.casa import DETECT_CASA


def inventory_casa_fan(section: Sequence[StringTable]) -> DiscoveryResult:
    inventory = []
    for nr, _speed in section[0]:
        inventory.append((nr, None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


def check_casa_fan(item: str, section: Sequence[StringTable]) -> CheckResult:
    for idx, (nr, speed) in enumerate(section[0]):
        if item == nr:
            fan_status = section[1][idx][1]
            if fan_status == "1":
                yield Result(state=State.OK, summary="%s RPM" % speed)
                return
            if fan_status == "3":
                yield Result(state=State.WARN, summary="%s RPM, running over threshold (!)" % speed)
                return
            if fan_status == "2":
                yield Result(
                    state=State.WARN, summary="%s RPM, running under threshold (!)" % speed
                )
                return
            if fan_status == "0":
                yield Result(state=State.UNKNOWN, summary="%s RPM, unknown fan status (!)" % speed)
                return
            if fan_status == "4":
                yield Result(state=State.CRIT, summary="FAN Failure (!!)")
                return
    yield Result(state=State.UNKNOWN, summary="Fan %s not found in snmp output" % item)
    return


def parse_casa_fan(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_casa_fan = SNMPSection(
    name="casa_fan",
    detect=DETECT_CASA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.31.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.33.1.4.1",
            oids=[OIDEnd(), "4"],
        ),
    ],
    parse_function=parse_casa_fan,
)
check_plugin_casa_fan = CheckPlugin(
    name="casa_fan",
    service_name="Fan %s",
    discovery_function=inventory_casa_fan,
    check_function=check_casa_fan,
)
