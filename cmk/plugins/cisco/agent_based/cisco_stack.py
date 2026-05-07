#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


@dataclass(frozen=True)
class Switch:
    role: str
    state: str


Section = Mapping[str, Switch]


def parse_cisco_stack(string_table: StringTable) -> Section:
    switch_state_names = {
        "1": "waiting",
        "2": "progressing",
        "3": "added",
        "4": "ready",
        "5": "sdmMismatch",
        "6": "verMismatch",
        "7": "featureMismatch",
        "8": "newMasterInit",
        "9": "provisioned",
        "10": "invalid",
        "11": "removed",
    }

    switch_role_names = {
        "1": "master",
        "2": "member",
        "3": "notMember",
        "4": "standby",
    }

    return {
        name: Switch(
            role=switch_role_names.get(role, "unknown"),
            state=switch_state_names.get(state, "unknown"),
        )
        for name, role, state in string_table
    }


snmp_section_cisco_stack = SimpleSNMPSection(
    name="cisco_stack",
    parse_function=parse_cisco_stack,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.500.1.2.1.1",
        oids=[
            "1",  # cswSwitchNumCurrent
            "3",  # cswSwitchRole
            "6",  # cswSwitchState
        ],
    ),
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1208"),  # cat29xxStack
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1745"),  # cat38xxstack
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.516"),  # catalyst37xxStack
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2694"),  # ciscoCat9200LFixedSwitchStack
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2695"),  # ciscoCat9200FixedSwitchStack
    ),
)


def discovery_cisco_stack(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_cisco_stack(item: str, params: Mapping[str, int], section: Section) -> CheckResult:
    switch_state_descriptions = {
        "waiting": "Waiting for other switches to come online",
        "progressing": "Master election or mismatch checks in progress",
        "added": "Added to stack",
        "ready": "Ready",
        "sdmMismatch": "SDM template mismatch",
        "verMismatch": "OS version mismatch",
        "featureMismatch": "Configured feature mismatch",
        "newMasterInit": "Waiting for new master initialization",
        "provisioned": "Not an active member of the stack",
        "invalid": "State machine in invalid state",
        "removed": "Removed from stack",
    }

    if (switch := section.get(item)) is None:
        return

    yield Result(
        state=State(params.get(switch.state, 3)),
        summary=f"Switch state: {switch_state_descriptions.get(switch.state, 'Unknown')} {switch.state}",
    )
    yield Result(state=State.OK, summary=f"Switch role: {switch.role}")


check_plugin_cisco_stack = CheckPlugin(
    name="cisco_stack",
    service_name="Switch stack status %s",
    discovery_function=discovery_cisco_stack,
    check_function=check_cisco_stack,
    check_default_parameters={
        "waiting": 0,
        "progressing": 0,
        "added": 0,
        "ready": 0,
        "sdmMismatch": 1,
        "verMismatch": 1,
        "featureMismatch": 1,
        "newMasterInit": 0,
        "provisioned": 0,
        "invalid": 2,
        "removed": 2,
    },
    check_ruleset_name="cisco_stack",
)
