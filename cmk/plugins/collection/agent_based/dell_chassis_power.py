#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
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


def inventory_dell_chassis_power(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_dell_chassis_power(section: StringTable) -> CheckResult:
    status, PotentialPower, MaxPowerSpec, power, current = section[0]
    state_table = {
        "1": ("other, ", State.WARN),
        "2": ("unknown, ", State.WARN),
        "3": ("", State.OK),
        "4": ("nonCritical, ", State.WARN),
        "5": ("Critical, ", State.CRIT),
        "6": ("NonRecoverable, ", State.CRIT),
    }
    infotext, state = state_table.get(status, ("unknown state, ", State.UNKNOWN))

    infotext += f"Power: {savefloat(power):.1f} W, PotentialPower: {savefloat(PotentialPower):.1f} W, MaxPower: {savefloat(MaxPowerSpec):.1f} W, Current: {savefloat(current):.1f} A"

    yield Result(state=state, summary=infotext)
    yield Metric("power", savefloat(power))


def parse_dell_chassis_power(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_dell_chassis_power = SimpleSNMPSection(
    name="dell_chassis_power",
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2",
        oids=["3.1.5.0", "4.1.1.2.1", "4.1.1.4.1", "4.1.1.13.1", "4.1.1.14.1"],
    ),
    parse_function=parse_dell_chassis_power,
)
check_plugin_dell_chassis_power = CheckPlugin(
    name="dell_chassis_power",
    service_name="Chassis Power",
    discovery_function=inventory_dell_chassis_power,
    check_function=check_dell_chassis_power,
)
