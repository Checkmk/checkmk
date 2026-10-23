#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SNMPSection,
    StringTable,
)
from cmk.plugins.huawei.lib import (
    HUARONG_ENTERPRISE,
    HUAWEI_ENTERPRISE,
    parse_huawei_physical_entity_values,
    Section,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def parse_huawei_switch_temp(string_table: Sequence[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table)


def discover_huawei_switch_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_huawei_switch_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (item_data := section.get(item)) is None or item_data.value is None:
        return
    try:
        temp = float(item_data.value)
    except TypeError:
        return
    yield from check_temperature(
        reading=temp,
        params=params,
        unique_name=f"huawei_switch_temp_{item_data.stack_member}",
        value_store=get_value_store(),
    )


snmp_section_huawei_switch_temp = SNMPSection(
    name="huawei_switch_temp",
    detect=HUAWEI_ENTERPRISE.switch_detect,
    fetch=HUAWEI_ENTERPRISE.entity_state_trees("11"),
    parse_function=parse_huawei_switch_temp,
)

snmp_section_huawei_switch_temp_huarong = SNMPSection(
    name="huawei_switch_temp_huarong",
    parsed_section_name="huawei_switch_temp",
    detect=HUARONG_ENTERPRISE.switch_detect,
    fetch=HUARONG_ENTERPRISE.entity_state_trees("11"),
    parse_function=parse_huawei_switch_temp,
)


check_plugin_huawei_switch_temp = CheckPlugin(
    name="huawei_switch_temp",
    service_name="Temperature %s",
    discovery_function=discover_huawei_switch_temp,
    check_function=check_huawei_switch_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
