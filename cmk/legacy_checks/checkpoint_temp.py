#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.checkpoint.lib import DETECT, SENSOR_STATUS_TO_CMK_STATUS
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def format_item_checkpoint_temp(name: str) -> str:
    return name.upper().replace(" TEMP", "")


def parse_checkpoint_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_checkpoint_temp(section: StringTable) -> DiscoveryResult:
    for name, _value, _unit, _dev_status in section:
        yield Service(item=format_item_checkpoint_temp(name))


def check_checkpoint_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for name, value, unit, dev_status in section:
        if format_item_checkpoint_temp(name) != item:
            continue
        unit = unit.replace("degree", "").strip().lower()
        state, state_readable = SENSOR_STATUS_TO_CMK_STATUS[dev_status]

        if value == "":
            yield Result(state=state, summary=f"Status: {state_readable}")
            return

        yield from check_temperature(
            float(value),
            params,
            dev_unit=unit,
            dev_status=state.value,
            dev_status_name=state_readable,
        )
        return


snmp_section_checkpoint_temp = SimpleSNMPSection(
    name="checkpoint_temp",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.8.1.1",
        oids=["2", "3", "4", "6"],
    ),
    parse_function=parse_checkpoint_temp,
)


check_plugin_checkpoint_temp = CheckPlugin(
    name="checkpoint_temp",
    service_name="Temperature %s",
    discovery_function=discover_checkpoint_temp,
    check_function=check_checkpoint_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (50.0, 60.0)},
)
