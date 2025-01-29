#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def inventory_dell_idrac_raid(section: Sequence[StringTable]) -> DiscoveryResult:
    for index, _name, _status in section[0]:
        yield Service(item=index)


def check_dell_idrac_raid(item: str, section: Sequence[StringTable]) -> CheckResult:
    translate_status = {
        "1": (State.UNKNOWN, "other"),
        "2": (State.UNKNOWN, "unknown"),
        "3": (State.OK, "OK"),
        "4": (State.WARN, "non-critical"),
        "5": (State.CRIT, "critical"),
        "6": (State.CRIT, "non-recoverable"),
    }

    for index, name, status in section[0]:
        if index == item:
            state, state_readable = translate_status[status]
            yield Result(state=state, summary=f"Status of {name}: {state_readable}")


def parse_dell_idrac_raid(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_dell_idrac_raid = SNMPSection(
    name="dell_idrac_raid",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.5"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.5.1.20.130.1.1",
            oids=["1", "2", "38"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.5.1.20.130.15.1",
            oids=["1", "4", "6", "21"],
        ),
    ],
    parse_function=parse_dell_idrac_raid,
)
check_plugin_dell_idrac_raid = CheckPlugin(
    name="dell_idrac_raid",
    service_name="Raid Controller %s",
    discovery_function=inventory_dell_idrac_raid,
    check_function=check_dell_idrac_raid,
)


def inventory_dell_idrac_raid_bbu(section: Sequence[StringTable]) -> DiscoveryResult:
    for index, _status, _comp_status, _name in section[1]:
        yield Service(item=index)


def check_dell_idrac_raid_bbu(item: str, section: Sequence[StringTable]) -> CheckResult:
    translate_bbu_status = {
        "1": (State.UNKNOWN, "UNKNOWN"),
        "2": (State.OK, "READY"),
        "3": (State.CRIT, "FAILED"),
        "4": (State.WARN, "DEGRADED"),
        "5": (State.UNKNOWN, "MISSING"),
        "6": (State.WARN, "CHARGING"),
        "7": (State.CRIT, "BELOW THRESHOLD"),
    }

    for index, status, _comp_status, _name in section[1]:
        if index == item:
            state, state_readable = translate_bbu_status[status]
            yield Result(state=state, summary="Battery status: %s" % state_readable)


check_plugin_dell_idrac_raid_bbu = CheckPlugin(
    name="dell_idrac_raid_bbu",
    service_name="Raid BBU %s",
    sections=["dell_idrac_raid"],
    discovery_function=inventory_dell_idrac_raid_bbu,
    check_function=check_dell_idrac_raid_bbu,
)
