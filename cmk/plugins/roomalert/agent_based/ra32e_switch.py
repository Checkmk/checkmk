#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.roomalert.lib import DETECT_RA32E


def discover_ra32e_switch(section: StringTable) -> DiscoveryResult:
    for index, _ in enumerate(section[0], start=1):
        yield Service(item=f"Sensor {index:02}")


def check_ra32e_switch(item: str, params: Mapping[str, str], section: StringTable) -> CheckResult:
    index = int(item.rsplit(maxsplit=1)[-1].lstrip("0")) - 1  # e.g. 'Sensor 08'
    switch_state = {"0": "open", "1": "closed"}.get(section[0][index])
    if not switch_state:
        yield Result(state=State.UNKNOWN, summary="unknown status")
        return

    state, infotext = State.OK, switch_state
    if params["state"] != "ignore" and switch_state != params["state"]:
        state = State.CRIT
        infotext += f" (expected {params['state']})"

    yield Result(state=state, summary=infotext)


def parse_ra32e_switch(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_ra32e_switch = SimpleSNMPSection(
    name="ra32e_switch",
    parse_function=parse_ra32e_switch,
    detect=DETECT_RA32E,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.8.1.3",
        oids=[
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
        ],
    ),
)


check_plugin_ra32e_switch = CheckPlugin(
    name="ra32e_switch",
    service_name="Switch %s",
    discovery_function=discover_ra32e_switch,
    check_function=check_ra32e_switch,
    check_ruleset_name="switch_contact",
    check_default_parameters={"state": "ignore"},
)
