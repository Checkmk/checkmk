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
    State,
    StringTable,
)
from cmk.plugins.huawei.lib import (
    HUAWEI_ENTERPRISE,
    parse_huawei_physical_entity_values,
    Section,
)

huawei_switch_hw_oper_state_map = {
    "1": "notSupported",
    "2": "disabled",
    "3": "enabled",
    "4": "offline",
}


def parse_huawei_switch_psu(string_table: Sequence[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table, "power card")


def discover_huawei_switch_psu(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_huawei_switch_psu(item: str, section: Section) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    # TODO: this weird. Either we should not discover in this case, or let it crash during checking.
    if item_data.value is None:
        return

    # Only 'enabled' is OK, everything else is considered CRIT
    state = State.OK if item_data.value == "3" else State.CRIT
    status_text = huawei_switch_hw_oper_state_map.get(
        item_data.value, f"unknown ({item_data.value})"
    )
    yield Result(state=state, summary=f"State: {status_text}")


snmp_section_huawei_switch_psu = SNMPSection(
    name="huawei_switch_psu",
    detect=HUAWEI_ENTERPRISE.switch_detect,
    fetch=HUAWEI_ENTERPRISE.entity_state_trees("2"),
    parse_function=parse_huawei_switch_psu,
)


check_plugin_huawei_switch_psu = CheckPlugin(
    name="huawei_switch_psu",
    service_name="Powersupply %s",
    discovery_function=discover_huawei_switch_psu,
    check_function=check_huawei_switch_psu,
)
