#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import TypedDict

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
from cmk.plugins.huawei.lib import DETECT_HUAWEI_SWITCH

_UNKNOWN_ROLE = "unknown"

_STACK_ROLE_NAMES = {
    "1": "master",
    "2": "standby",
    "3": "slave",
}

Section = Mapping[str, str]


class HuaweiSwitchStackParams(TypedDict):
    expected_role: str


def parse_huawei_switch_stack(string_table: Sequence[StringTable]) -> Section:
    stack_enabled_info, stack_role_info = string_table
    if not stack_enabled_info or stack_enabled_info[0][0] != "1":
        return {}

    return {line[0]: _STACK_ROLE_NAMES.get(line[1], _UNKNOWN_ROLE) for line in stack_role_info}


def discover_huawei_switch_stack(section: Section) -> DiscoveryResult:
    for item, role in section.items():
        yield Service(item=item, parameters={"expected_role": role})


def check_huawei_switch_stack(
    item: str, params: HuaweiSwitchStackParams, section: Section
) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    if item_data == _UNKNOWN_ROLE:
        yield Result(state=State.CRIT, summary=item_data)
    elif item_data == params["expected_role"]:
        yield Result(state=State.OK, summary=item_data)
    else:
        yield Result(
            state=State.CRIT,
            summary=f"Unexpected role: {item_data} (Expected: {params['expected_role']})",
        )


snmp_section_huawei_switch_stack = SNMPSection(
    name="huawei_switch_stack",
    detect=DETECT_HUAWEI_SWITCH,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.183.1",
            oids=["5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.183.1.20.1",
            oids=[OIDEnd(), "3"],
        ),
    ],
    parse_function=parse_huawei_switch_stack,
)


check_plugin_huawei_switch_stack = CheckPlugin(
    name="huawei_switch_stack",
    service_name="Stack role %s",
    discovery_function=discover_huawei_switch_stack,
    check_function=check_huawei_switch_stack,
    check_default_parameters={"expected_role": "unknown"},
)
