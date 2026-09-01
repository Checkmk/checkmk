#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
#
# <<<ucsc_server_temp:sep(9)>>>
# processorEnvStats<TAB>dn sys/rack-unit-1/board/cpu-1/env-stats<TAB>id 1<TAB>description blalub<TAB>temperature 58.4
# processorEnvStats<TAB>dn sys/rack-unit-1/board/cpu-2/env-stats<TAB>id 2<TAB>description blalub<TAB>temperature 50.4
# memoryUnitEnvStats<TAB>dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats<TAB>id 1<TAB>description blalub<TAB>temperature 40.4
# memoryUnitEnvStats<TAB>dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats<TAB>id 2<TAB>description blalub<TAB>temperature 41.4
# computeRackUnitMbTempStats<TAB>dn sys/rack-unit-1/board/temp-stats<TAB>ambientTemp 50.0<TAB>frontTemp 50.0<TAB>ioh1Temp 50.0<TAB>ioh2Temp 50.0<TAB>rearTemp 50.0
# computeRackUnitMbTempStats<TAB>dn sys/rack-unit-2/board/temp-stats<TAB>ambientTemp 50.0<TAB>frontTemp 50.0<TAB>ioh1Temp 50.0<TAB>ioh2Temp 50.0<TAB>rearTemp 50.0


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

type Section = Mapping[str, float]


def parse_ucs_c_rack_server_temp(string_table: StringTable) -> Section:
    """
    Returns dict with indexed processors, memory units and motherboards mapped to keys and
    temperature as value.
    """
    parsed = {}
    for line in string_table:
        key_value_pairs = [kv.split(" ", 1) for kv in line[1:]]
        if "cpu-" in key_value_pairs[0][1]:
            item = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/board", "")
                .replace("/cpu-", " CPU ")
                .replace("/env-stats", "")
            )
            temperature_index = 3
        elif "mem-" in key_value_pairs[0][1]:
            item = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/board", "")
                .replace("/memarray-", " Memory Array ")
                .replace("/mem-", " Memory DIMM ")
                .replace("/dimm-env-stats", "")
            )
            temperature_index = 3
        elif "board" in key_value_pairs[0][1]:
            item = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/board/temp-stats", " Motherboard")
            )
            temperature_index = 2
        else:
            continue  # skip potentially invalid agent output

        try:
            parsed[item] = float(key_value_pairs[temperature_index][1])
        except ValueError, KeyError:
            continue  # skip potentially invalid agent output
    return parsed


def discover_ucs_c_rack_server_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ucs_c_rack_server_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    if (temperature := section.get(item)) is None:
        return

    yield from check_temperature(
        temperature,
        params,
        unique_name="ucs_c_rack_server_%s" % item.lower().replace(" ", "_"),
        value_store=get_value_store(),
    )


agent_section_ucs_c_rack_server_temp = AgentSection(
    name="ucs_c_rack_server_temp",
    parse_function=parse_ucs_c_rack_server_temp,
)


check_plugin_ucs_c_rack_server_temp = CheckPlugin(
    name="ucs_c_rack_server_temp",
    service_name="Temperature %s",
    discovery_function=discover_ucs_c_rack_server_temp,
    check_function=check_ucs_c_rack_server_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
