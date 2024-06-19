#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


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


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def inventory_apc_mod_pdu_modules(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=x[0]) for x in section if x[0] != ""]


def check_apc_mod_pdu_modules(item: str, section: StringTable) -> CheckResult:
    apc_states = {
        1: "normal",
        2: "warning",
        3: "notPresent",
        6: "unknown",
    }
    for name, status_r, current_power_r in section:
        if name == item:
            status = saveint(status_r)
            # As per the device's MIB, the values are measured in tenths of kW
            current_power = savefloat(current_power_r) / 10
            message = f"Status {apc_states.get(status, 6)}, current: {current_power:.2f} kW"

            yield Metric("power", current_power * 1000)
            if status == 2:
                yield Result(state=State.WARN, summary=message)
                return

            if status in [3, 6]:
                yield Result(state=State.CRIT, summary=message)
                return

            if status == 1:
                yield Result(state=State.OK, summary=message)
                return

            yield Result(state=State.UNKNOWN, summary=message)
            return

    return


def parse_apc_mod_pdu_modules(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_apc_mod_pdu_modules = SimpleSNMPSection(
    name="apc_mod_pdu_modules",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.24.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.22.2.6.1",
        oids=["4", "6", "20"],
    ),
    parse_function=parse_apc_mod_pdu_modules,
)
check_plugin_apc_mod_pdu_modules = CheckPlugin(
    name="apc_mod_pdu_modules",
    service_name="Module %s",
    discovery_function=inventory_apc_mod_pdu_modules,
    check_function=check_apc_mod_pdu_modules,
)
