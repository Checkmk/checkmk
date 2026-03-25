#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
)
from cmk.plugins.hwg.agent_based.lib import parse_hwg
from cmk.plugins.lib.temperature import check_temperature, TempParamType

HWG_TEMP_DEFAULTLEVELS = {"levels": (30.0, 35.0)}

READABLE_STATES: Mapping[str, State] = {
    "invalid": State.UNKNOWN,
    "normal": State.OK,
    "out of range low": State.CRIT,
    "out of range high": State.CRIT,
    "alarm low": State.CRIT,
    "alarm high": State.CRIT,
}


def discover_hwg_temp(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for index, attrs in section.items():
        if attrs.get("temperature") and attrs["dev_status_name"] not in ["invalid", ""]:
            yield Service(item=index)


def check_hwg_temp(
    item: str, params: TempParamType, section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    if not (data := section.get(item)):
        return
    state = READABLE_STATES.get(data["dev_status_name"], State.UNKNOWN)
    state_readable = data["dev_status_name"]
    temp = data["temperature"]
    if temp is None:
        yield Result(state=state, summary=f"Status: {state_readable}")
        return

    yield from check_temperature(
        temp,
        params,
        unique_name=f"hwg_temp_{item}",
        value_store=get_value_store(),
        dev_unit=data["dev_unit"],
        dev_status=state.value,
        dev_status_name=state_readable,
    )
    yield Result(
        state=State.OK,
        summary=f"Description: {data['descr']}, Status: {data['dev_status_name']}",
    )


snmp_section_hwg_temp = SimpleSNMPSection(
    name="hwg_temp",
    detect=contains(".1.3.6.1.2.1.1.1.0", "hwg"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.4.1.3.1",
        oids=["1", "2", "3", "4", "7"],
    ),
    parse_function=parse_hwg,
)


check_plugin_hwg_temp = CheckPlugin(
    name="hwg_temp",
    service_name="Temperature %s",
    discovery_function=discover_hwg_temp,
    check_function=check_hwg_temp,
    check_ruleset_name="temperature",
    check_default_parameters=HWG_TEMP_DEFAULTLEVELS,
)

snmp_section_hwg_ste2 = SimpleSNMPSection(
    name="hwg_ste2",
    detect=contains(".1.3.6.1.2.1.1.1.0", "STE2"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.4.9.3.1",
        oids=["1", "2", "3", "4", "7"],
    ),
    parse_function=parse_hwg,
)


check_plugin_hwg_ste2 = CheckPlugin(
    name="hwg_ste2",
    sections=["hwg_ste2"],
    service_name="Temperature %s",
    discovery_function=discover_hwg_temp,
    check_function=check_hwg_temp,
    check_ruleset_name="temperature",
    check_default_parameters=HWG_TEMP_DEFAULTLEVELS,
)
