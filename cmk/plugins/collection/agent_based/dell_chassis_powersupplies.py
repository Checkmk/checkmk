#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.dell import DETECT_CHASSIS


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def inventory_dell_chassis_powersupplies(section: StringTable) -> DiscoveryResult:
    inventory = []
    for line in section:
        item = re.sub(r"\.", "-", line[0])
        inventory.append((item, None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


def check_dell_chassis_powersupplies(item: str, section: StringTable) -> CheckResult:
    for oid_end, voltage, current, maxpower in section:
        if item == re.sub(r"\.", "-", oid_end):
            power = savefloat(voltage) * savefloat(current)
            infotext = f"current/max Power: {power:.2f} / {maxpower}, Current: {current}, Voltage: {voltage}"

            if savefloat(current) == 0:
                infotext = infotext + " - device in standby"

            yield Result(state=State.OK, summary=infotext)
            yield Metric("power", power)
            return

    yield Result(state=State.UNKNOWN, summary="unknown power supply")
    return


def parse_dell_chassis_powersupplies(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_chassis_powersupplies = SimpleSNMPSection(
    name="dell_chassis_powersupplies",
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2.4.2.1",
        oids=[OIDEnd(), "5", "6", "7"],
    ),
    parse_function=parse_dell_chassis_powersupplies,
)
check_plugin_dell_chassis_powersupplies = CheckPlugin(
    name="dell_chassis_powersupplies",
    service_name="Power Supply %s",
    discovery_function=inventory_dell_chassis_powersupplies,
    check_function=check_dell_chassis_powersupplies,
)
