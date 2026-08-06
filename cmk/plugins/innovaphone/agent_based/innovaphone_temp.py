#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def discover_innovaphone_temp(section: StringTable) -> DiscoveryResult:
    yield Service(item="Ambient")


def check_innovaphone_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    yield from check_temperature(
        int(section[0][1]),
        params,
        unique_name=f"innovaphone_temp_{item}",
        value_store=get_value_store(),
    )


def parse_innovaphone_temp(string_table: StringTable) -> StringTable:
    return string_table


agent_section_innovaphone_temp = AgentSection(
    name="innovaphone_temp",
    parse_function=parse_innovaphone_temp,
)


check_plugin_innovaphone_temp = CheckPlugin(
    name="innovaphone_temp",
    service_name="Temperature %s",
    discovery_function=discover_innovaphone_temp,
    check_function=check_innovaphone_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (45.0, 50.0)},
)
