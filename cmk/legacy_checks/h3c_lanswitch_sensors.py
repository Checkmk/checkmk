#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

Section = Mapping[str, str]


def parse_h3c_lanswitch_sensors(string_table: Sequence[StringTable]) -> Section:
    return {
        h3c_lanswitch_genitem(device_class, item): state
        for device_class, string_table in zip(("Fan", "Powersupply"), string_table)
        for item, state in string_table
    }


def discover_h3c_lanswitch_sensors(section: Section) -> DiscoveryResult:
    yield from [Service(item=item) for item, state in section.items() if state in ["1", "2"]]


def check_h3c_lanswitch_sensors(item: str, section: Section) -> CheckResult:
    if (status := section.get(item)) is None:
        return

    # the values are:   active     (1), deactive   (2), not-install  (3), unsupport    (4)
    match status:
        case "2":
            yield Result(state=State.CRIT, summary=f"Sensor {item} status is {status}")
        case "1":
            yield Result(state=State.OK, summary=f"Sensor {item} status is {status}")
        case _:
            yield Result(state=State.WARN, summary=f"Sensor {item: }tatus is {status}")


snmp_section_h3c_lanswitch_sensors = SNMPSection(
    name="h3c_lanswitch_sensors",
    detect=contains(".1.3.6.1.2.1.1.1.0", "3com s"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.43.45.1.2.23.1.9.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.43.45.1.2.23.1.9.1.2.1",
            oids=[OIDEnd(), "2"],
        ),
    ],
    parse_function=parse_h3c_lanswitch_sensors,
)


check_plugin_h3c_lanswitch_sensors = CheckPlugin(
    name="h3c_lanswitch_sensors",
    service_name="%s",
    discovery_function=discover_h3c_lanswitch_sensors,
    check_function=check_h3c_lanswitch_sensors,
)


def h3c_lanswitch_genitem(device_class: str, id_: str) -> str:
    unitid = int(id_) // 65536
    num = int(id_) % 65536
    return "Unit %d %s %d" % (unitid, device_class, num)
